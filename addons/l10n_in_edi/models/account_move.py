import base64
import json
import logging
import re
from collections import defaultdict

from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, LockError, UserError
from odoo.tools import float_is_zero, float_compare

from odoo.addons.l10n_in.models.account_invoice import EDI_CANCEL_REASON

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # E-Invoice Fields
    l10n_in_edi_status = fields.Selection(
        string="India E-Invoice Status",
        selection=[
            ('to_send', "To Send"),
            ('sent', "Sent"),
            ('cancelled', "Cancelled"),
        ],
        copy=False,
        tracking=True,
        readonly=True,
        store=True,
        compute="_compute_l10n_in_edi_status",
    )
    l10n_in_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="E-Invoice(IN) Attachment",
        compute=lambda self: self._compute_linked_attachment_id(
            'l10n_in_edi_attachment_id',
            'l10n_in_edi_attachment_file'
        ),
        depends=['l10n_in_edi_attachment_file']
    )
    l10n_in_edi_attachment_file = fields.Binary(
        string="E-Invoice(IN) File",
        attachment=True,
        copy=False
    )
    l10n_in_edi_cancel_reason = fields.Selection(
        selection=list(EDI_CANCEL_REASON.items()),
        string="E-Invoice(IN) Cancel Reason",
        copy=False
    )
    l10n_in_edi_cancel_remarks = fields.Char(
        string="E-Invoice(IN) Cancel Remarks",
        copy=False
    )
    l10n_in_edi_content = fields.Binary(
        compute="_compute_l10n_in_edi_content",
        string="E-Invoice(IN) Content"
    )
    l10n_in_edi_error = fields.Html(readonly=True, copy=False)

    # E-Invoice compute
    @api.depends('state')
    def _compute_l10n_in_edi_status(self):
        self.filtered(
            lambda m: m.state == 'posted' and m._l10n_in_check_einvoice_eligible()
        ).l10n_in_edi_status = 'to_send'

    def _compute_l10n_in_edi_content(self):
        for move in self:
            move.l10n_in_edi_content = (
                move.country_code == 'IN'
                and move.company_id.l10n_in_edi_feature
                and move.is_sale_document(include_receipts=True)
                and move.journal_id.type == 'sale'
                and base64.b64encode(
                    json.dumps(move._l10n_in_edi_generate_invoice_json()).encode()
                )
            )

    #  Action Methods
    def action_export_l10n_in_edi_content_json(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/account.move/{self.id}/l10n_in_edi_content'
        }

    def button_request_cancel(self):
        if self._l10n_in_edi_need_cancel_request():
            if self.l10n_in_edi_cancel_remarks and self.l10n_in_edi_cancel_reason:
                return self._l10n_in_edi_cancel_invoice()
            return self.env['l10n_in_edi.cancel'].with_context(
                default_move_id=self.id
            )._get_records_action(name=_("Cancel E-Invoice"), target='new')
        elif self.l10n_in_edi_status == 'sent':
            self.message_post(
                body=_(
                    "Force cancelled %(invoice)s by %(username)s",
                    invoice=self.name, username=self.env.user.name
                )
            )
            self.button_cancel()
            self.write({
                'l10n_in_edi_status': 'cancelled',
                'l10n_in_edi_error': False,
            })
            return True
        return super().button_request_cancel()

    def action_l10n_in_edi_force_cancel(self):
        self.with_context(l10n_in_edi_force_cancel=True).button_request_cancel()

    def button_draft(self):
        self.filtered(lambda m: m.l10n_in_edi_error).l10n_in_edi_error = False
        return super().button_draft()

    # Business Methods
    def _l10n_in_edi_need_cancel_request(self):
        self.ensure_one()
        return (
            self.country_code == 'IN'
            and not self._context.get('l10n_in_edi_force_cancel')
            and self.is_sale_document()
            and self.l10n_in_edi_status == 'sent'
        )

    def _need_cancel_request(self):
        # EXTENDS 'account'
        return super()._need_cancel_request() or self._l10n_in_edi_need_cancel_request()

    # Indian E-invoice Business Methods
    def _l10n_in_check_einvoice_eligible(self):
        self.ensure_one()
        return (
            self.country_code == 'IN'
            and self.company_id.l10n_in_edi_feature
            and self.is_sale_document(include_receipts=True)
            and self.journal_id.type == 'sale'
            and self.l10n_in_gst_treatment in (
                'regular',
                'composition',
                'overseas',
                'special_economic_zone',
                'deemed_export',
            )
            and any(tag.id in self._get_l10n_in_gst_tags() for tag in self.line_ids.tax_tag_ids)
        )

    def _get_l10n_in_edi_response_json(self):
        self.ensure_one()
        if self.l10n_in_edi_attachment_id:
            return json.loads(self.l10n_in_edi_attachment_id.sudo().raw.decode("utf-8"))

    def _l10n_in_lock_invoice(self):
        try:
            self.lock_for_update()
        except LockError:
            raise UserError(_('This electronic document is being processed already.')) from None

    def _l10n_in_edi_send_invoice(self):
        self.ensure_one()
        if self.l10n_in_edi_error:
            # make sure to clear the error before sending again
            self.l10n_in_edi_error = False
        partners = set(self._get_l10n_in_seller_buyer_party().values())
        for partner in partners:
            if partner_validation := partner._l10n_in_edi_strict_error_validation():
                return partner_validation
        self._l10n_in_lock_invoice()
        generate_json = self._l10n_in_edi_generate_invoice_json()
        response = self._l10n_in_edi_connect_to_server(
            url_end_point='generate',
            json_payload=generate_json
        )
        if error := response.get('error', {}):
            odoobot_id = self.env.ref('base.partner_root').id
            error_codes = [e.get("code") for e in error]
            if '2150' in error_codes:
                # Get IRN by details in case of IRN is already generated
                # this happens when timeout from the Government portal but IRN is generated
                response = self._l10n_in_edi_connect_to_server(
                    url_end_point='getirnbydocdetails',
                    params={
                        "doc_type": (
                            (self.move_type == "out_refund" and "CRN")
                            or (self.debit_origin_id and "DBN")
                            or "INV"
                        ),
                        "doc_num": self.name,
                        "doc_date": self.invoice_date and self.invoice_date.strftime("%d/%m/%Y"),
                    }
                )
                if not response.get("error"):
                    error = []
                    link = Markup(
                        "<a href='https://einvoice1.gst.gov.in/Others/VSignedInvoice'>%s</a>"
                    ) % (_("here"))
                    self.message_post(
                        author_id=odoobot_id,
                        body=_(
                            "Somehow this invoice has been submited to government before."
                            "%(br)sNormally, this should not happen too often"
                            "%(br)sJust verify value of invoice by upload json to government website %(link)s.",
                            br=Markup("<br/>"),
                            link=link
                        )
                    )
            if (no_credit := 'no-credit' in error_codes) or error:
                msg = Markup("<br/>").join(
                    ["[%s] %s" % (e.get("code"), e.get("message")) for e in error]
                )
                self.l10n_in_edi_error = (
                    self._l10n_in_edi_get_iap_buy_credits_message()
                    if no_credit else msg
                )
                # avoid return `l10n_in_edi_error` because as a html field
                # values are sanitized with `<p>` tag
                return msg
        data = response.get("data", {})
        json_dump = json.dumps(data)
        json_name = "%s_einvoice.json" % (self.name.replace("/", "_"))
        attachment = self.env["ir.attachment"].create({
            'name': json_name,
            'raw': json_dump.encode(),
            'res_model': self._name,
            'res_field': 'l10n_in_edi_attachment_file',
            'res_id': self.id,
            'mimetype': 'application/json',
            'company_id': self.company_id.id,
        })
        self.l10n_in_edi_status = 'sent'

    def _l10n_in_edi_cancel_invoice(self):
        if self.l10n_in_edi_error:
            # make sure to clear the error before cancelling again
            self.l10n_in_edi_error = False
        self._l10n_in_lock_invoice()
        l10n_in_edi_response_json = self._get_l10n_in_edi_response_json()
        cancel_json = {
            "Irn": l10n_in_edi_response_json.get("Irn"),
            "CnlRsn": self.l10n_in_edi_cancel_reason,
            "CnlRem": self.l10n_in_edi_cancel_remarks,
        }
        response = self._l10n_in_edi_connect_to_server(url_end_point='cancel', json_payload=cancel_json)
        # Creating a lambda function so it fetches the odoobot id only when needed
        _get_odoobot_id = (
            lambda self: self.env.ref('base.partner_root').id
        )
        if error := response.get('error'):
            error_codes = [e.get('code') for e in error]
            if '9999' in error_codes:
                response = {}
                error = []
                link = Markup(
                    "<a href='https://einvoice1.gst.gov.in/Others/VSignedInvoice'>%s</a>"
                ) % (_("here"))
                self.message_post(
                    author_id=_get_odoobot_id(self),
                    body=_(
                        "Somehow this invoice had been cancelled to government before."
                        "%(br)sNormally, this should not happen too often"
                        "%(br)sJust verify by logging into government website %(link)s",
                        br=Markup("<br/>"),
                        link=link
                    )
                )
            if "no-credit" in error_codes:
                self.l10n_in_edi_error = self._l10n_in_edi_get_iap_buy_credits_message()
                return
            if error:
                self.l10n_in_edi_error = (
                    Markup("<br/>").join(
                        ["[%s] %s" % (e.get("code"), e.get("message")) for e in error]
                    )
                )
        if "error" not in response:
            json_dump = json.dumps(response.get('data', {}))
            json_name = "%s_cancel_einvoice.json" % (self.name.replace("/", "_"))
            if json_dump:
                attachment = self.env['ir.attachment'].create({
                    'name': json_name,
                    'raw': json_dump.encode(),
                    'res_model': self._name,
                    'res_field': 'l10n_in_edi_attachment_file',
                    'res_id': self.id,
                    'mimetype': 'application/json',
                })
            self.message_post(author_id=_get_odoobot_id(self), body=_(
                "E-Invoice has been cancelled successfully. "
                "Cancellation Reason: %(reason)s and Cancellation Remark: %(remark)s",
                reason=EDI_CANCEL_REASON[self.l10n_in_edi_cancel_reason],
                remark=self.l10n_in_edi_cancel_remarks
            ))
            self.l10n_in_edi_status = 'cancelled'
            self.button_cancel()
        if self._can_commit():
            self._cr.commit()
        return True

    @api.model
    def _get_l10n_in_edi_partner_details(
            self,
            partner,
            set_vat=True,
            set_phone_and_email=True,
            is_overseas=False,
            pos_state_id=False
    ):
        """
            Create the dictionary based partner details
            if set_vat is true then, vat(GSTIN) and legal name(LglNm) is added
            if set_phone_and_email is true then phone and email is add
            if set_pos is true then state code from partner
             or passed state_id is added as POS(place of supply)
            if is_overseas is true then pin is 999999 and GSTIN(vat) is URP and Stcd is .
            if pos_state_id is passed then we use set POS
        """
        zip_digits = self._l10n_in_extract_digits(partner.zip)
        partner_details = {
            'Addr1': partner.street or '',
            'Loc': partner.city or '',
            'Pin': zip_digits and int(zip_digits) or '',
            'Stcd': partner.state_id.l10n_in_tin or '',
        }
        if partner.street2:
            partner_details['Addr2'] = partner.street2
        if set_phone_and_email:
            if partner.email:
                partner_details['Em'] = partner.email
            if partner.phone:
                partner_details['Ph'] = self._l10n_in_extract_digits(partner.phone)
        if pos_state_id:
            partner_details['POS'] = pos_state_id.l10n_in_tin or ''
        if set_vat:
            partner_details.update({
                'LglNm': partner.commercial_partner_id.name,
                'GSTIN': partner.vat or 'URP',
            })
        else:
            partner_details['Nm'] = partner.name
        # For no country I would suppose it is India, so not sure this is super right
        if is_overseas and (not partner.country_id or partner.country_id.code != 'IN'):
            partner_details.update({
                "GSTIN": "URP",
                "Pin": 999999,
                "Stcd": "96",
                "POS": "96",
            })
        return partner_details

    def _get_l10n_in_edi_line_details(self, index, line, line_tax_details):
        """
        Create the dictionary with line details
        """
        sign = self.is_inbound() and -1 or 1
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(line_tax_details['tax_details'])
        quantity = line.quantity
        if line.discount == 100.00 or float_is_zero(quantity, 3):
            # Full discount or zero quantity
            unit_price_in_inr = line.currency_id._convert(
                line.price_unit,
                line.company_currency_id,
                line.company_id,
                line.date or fields.Date.context_today(self)
            )
        else:
            unit_price_in_inr = ((sign * line.balance) / (1 - (line.discount / 100))) / quantity

        if unit_price_in_inr < 0 and quantity < 0:
            # If unit price and quantity both is negative then
            # We set unit price and quantity as positive because
            # government does not accept negative in qty or unit price
            unit_price_in_inr = -unit_price_in_inr
            quantity = -quantity
        in_round = self._l10n_in_round_value
        return {
            'SlNo': str(index),
            'PrdDesc': (line.product_id.display_name or line.name).replace("\n", ""),
            'IsServc': line.product_id.type == 'service' and 'Y' or 'N',
            'HsnCd': self._l10n_in_extract_digits(line.l10n_in_hsn_code),
            'Qty': in_round(quantity or 0.0, 3),
            'Unit': (
                line.product_uom_id.l10n_in_code
                and line.product_uom_id.l10n_in_code.split('-')[0]
                or 'OTH'
            ),
            # Unit price in company currency and tax excluded so its different then price_unit
            'UnitPrice': in_round(unit_price_in_inr, 3),
            # total amount is before discount
            'TotAmt': in_round(unit_price_in_inr * quantity),
            'Discount': in_round((unit_price_in_inr * quantity) * (line.discount / 100)),
            'AssAmt': in_round(sign * line.balance),
            'GstRt': in_round(
                (tax_details_by_code.get('igst_rate', 0.00)
                or (tax_details_by_code.get('cgst_rate', 0.00) + tax_details_by_code.get('sgst_rate', 0.00))),
                3
            ),
            'IgstAmt': in_round(tax_details_by_code.get('igst_amount', 0.00)),
            'CgstAmt': in_round(tax_details_by_code.get('cgst_amount', 0.00)),
            'SgstAmt': in_round(tax_details_by_code.get('sgst_amount', 0.00)),
            'CesRt': in_round(tax_details_by_code.get('cess_rate', 0.00), 3),
            'CesAmt': in_round(tax_details_by_code.get('cess_amount', 0.00)),
            'CesNonAdvlAmt': in_round(
                tax_details_by_code.get('cess_non_advol_amount', 0.00)
            ),
            'StateCesRt': in_round(tax_details_by_code.get('state_cess_rate_amount', 0.00), 3),
            'StateCesAmt': in_round(tax_details_by_code.get('state_cess_amount', 0.00)),
            'StateCesNonAdvlAmt': in_round(
                tax_details_by_code.get('state_cess_non_advol_amount', 0.00)
            ),
            'OthChrg': in_round(tax_details_by_code.get('other_amount', 0.00)),
            'TotItemVal': in_round((sign * line.balance) + line_tax_details.get('tax_amount', 0.00)),
        }

    def _l10n_in_edi_generate_invoice_json_managing_negative_lines(self, json_payload):
        """Set negative lines against positive lines as discount with same HSN code and tax rate
            With negative lines
            product name | hsn code | unit price | qty | discount | total
            =============================================================
            product A    | 123456   | 1000       | 1   | 100      |  900
            product B    | 123456   | 1500       | 2   | 0        | 3000
            Discount     | 123456   | -300       | 1   | 0        | -300
            Converted to without negative lines
            product name | hsn code | unit price | qty | discount | total
            =============================================================
            product A    | 123456   | 1000       | 1   | 100      |  900
            product B    | 123456   | 1500       | 2   | 300      | 2700
            totally discounted lines are kept as 0, though
        """
        def discount_group_key(line_vals):
            return "%s-%s" % (line_vals['HsnCd'], line_vals['GstRt'])

        def put_discount_on(discount_line_vals, other_line_vals):
            discount = -discount_line_vals['AssAmt']
            discount_to_allow = other_line_vals['AssAmt']
            in_round = self._l10n_in_round_value
            amount_keys = (
                'AssAmt', 'IgstAmt', 'CgstAmt', 'SgstAmt', 'CesAmt',
                'CesNonAdvlAmt', 'StateCesAmt', 'StateCesNonAdvlAmt',
                'OthChrg', 'TotItemVal'
            )
            if float_compare(discount_to_allow, discount, precision_rounding=self.currency_id.rounding) < 0:
                # Update discount line, needed when discount is more then max line, in short remaining_discount is not zero
                discount_line_vals.update({
                    key: in_round(discount_line_vals[key] + other_line_vals[key])
                    for key in amount_keys
                })
                other_line_vals['Discount'] = in_round(other_line_vals['Discount'] + discount_to_allow)
                other_line_vals.update(dict.fromkeys(amount_keys, 0.00))
                return False
            other_line_vals['Discount'] = in_round(other_line_vals['Discount'] + discount)
            other_line_vals.update({
                key: in_round(other_line_vals[key] + discount_line_vals[key])
                for key in amount_keys
            })
            return True

        discount_lines = []
        for discount_line in json_payload['ItemList'].copy(): #to be sure to not skip in the loop:
            if discount_line['AssAmt'] < 0:
                discount_lines.append(discount_line)
                json_payload['ItemList'].remove(discount_line)
        if not discount_lines:
            return json_payload
        self.message_post(
            author_id=self.env.ref('base.partner_root').id,
            body=_("Negative lines will be decreased from positive invoice lines having the same taxes and HSN code")
        )

        lines_grouped_and_sorted = defaultdict(list)
        for line in sorted(json_payload['ItemList'], key=lambda i: i['AssAmt'], reverse=True):
            lines_grouped_and_sorted[discount_group_key(line)].append(line)

        for discount_line in discount_lines:
            for apply_discount_on in lines_grouped_and_sorted[discount_group_key(discount_line)]:
                if put_discount_on(discount_line, apply_discount_on):
                    break
        return json_payload

    def _l10n_in_edi_generate_invoice_json(self):
        self.ensure_one()
        tax_details = self._l10n_in_prepare_tax_details()
        seller_buyer = self._get_l10n_in_seller_buyer_party()
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details['tax_details'])
        is_intra_state = self.l10n_in_state_id == self.company_id.state_id
        is_overseas = self.l10n_in_gst_treatment == "overseas"
        line_ids = []
        global_discount_line_ids = []
        grouping_lines = self.invoice_line_ids.grouped(
            lambda l: l.display_type == 'product' and (l._l10n_in_is_global_discount() and 'global_discount' or 'lines')
        )
        default_line = self.env['account.move.line'].browse()
        lines = grouping_lines.get('lines', default_line)
        global_discount_line = grouping_lines.get('global_discount', default_line)
        tax_details_per_record = tax_details['tax_details_per_record']
        sign = self.is_inbound() and -1 or 1
        rounding_amount = sum(line.balance for line in self.line_ids if line.display_type == 'rounding') * sign
        global_discount_amount = sum(line.balance for line in global_discount_line) * -sign
        in_round = self._l10n_in_round_value
        json_payload = {
            "Version": "1.1",
            "TranDtls": {
                "TaxSch": "GST",
                "SupTyp": self._l10n_in_get_supply_type(tax_details_by_code.get('igst_amount')),
                "RegRev": tax_details_by_code.get('is_reverse_charge') and "Y" or "N",
                "IgstOnIntra": is_intra_state and tax_details_by_code.get('igst_amount') and "Y" or "N",
            },
            "DocDtls": {
                "Typ": (self.move_type == "out_refund" and "CRN") or (self.debit_origin_id and "DBN") or "INV",
                "No": self.name,
                "Dt": self.invoice_date and self.invoice_date.strftime("%d/%m/%Y")
            },
            "SellerDtls": self._get_l10n_in_edi_partner_details(seller_buyer['seller_details']),
            "BuyerDtls": self._get_l10n_in_edi_partner_details(
                seller_buyer['buyer_details'],
                pos_state_id=self.l10n_in_state_id,
                is_overseas=is_overseas
            ),
            "ItemList": [
                self._get_l10n_in_edi_line_details(
                    index,
                    line,
                    tax_details_per_record.get(line, {})
                )
                for index, line in enumerate(lines, start=1)
            ],
            "ValDtls": {
                "AssVal": in_round(tax_details['base_amount'] + global_discount_amount),
                "CgstVal": in_round(tax_details_by_code.get("cgst_amount", 0.00)),
                "SgstVal": in_round(tax_details_by_code.get("sgst_amount", 0.00)),
                "IgstVal": in_round(tax_details_by_code.get("igst_amount", 0.00)),
                "CesVal": in_round((
                    tax_details_by_code.get("cess_amount", 0.00)
                    + tax_details_by_code.get("cess_non_advol_amount", 0.00)),
                ),
                "StCesVal": in_round((
                    tax_details_by_code.get("state_cess_amount", 0.00)
                    + tax_details_by_code.get("state_cess_non_advol_amount", 0.00)), # clean this up =p
                ),
                "Discount": in_round(global_discount_amount),
                "RndOffAmt": in_round(rounding_amount),
                "TotInvVal": in_round(
                    (tax_details["base_amount"] + tax_details["tax_amount"] + rounding_amount)),
            },
        }
        if self.company_currency_id != self.currency_id:
            json_payload["ValDtls"].update({
                "TotInvValFc": in_round(
                    (tax_details.get("base_amount_currency") + tax_details.get("tax_amount_currency")))
            })
        if seller_buyer['seller_details'] != seller_buyer['dispatch_details']:
            json_payload['DispDtls'] = self._get_l10n_in_edi_partner_details(
                seller_buyer['dispatch_details'],
                set_vat=False,
                set_phone_and_email=False
            )
        if seller_buyer['buyer_details'] != seller_buyer['ship_to_details']:
            json_payload['ShipDtls'] = self._get_l10n_in_edi_partner_details(
                seller_buyer['ship_to_details'],
                is_overseas=is_overseas
            )
        if is_overseas:
            json_payload['ExpDtls'] = {
                'RefClm': tax_details_by_code.get('igst_amount') and 'Y' or 'N',
                'ForCur': self.currency_id.name,
                'CntCode': seller_buyer['buyer_details'].country_id.code or '',
            }
            if shipping_bill_no := self.l10n_in_shipping_bill_number:
                json_payload['ExpDtls']['ShipBNo'] = shipping_bill_no
            if shipping_bill_date := self.l10n_in_shipping_bill_date:
                json_payload['ExpDtls']['ShipBDt'] = shipping_bill_date.strftime("%d/%m/%Y")
            if shipping_port_code_id := self.l10n_in_shipping_port_code_id:
                json_payload['ExpDtls']['Port'] = shipping_port_code_id.code
        return self._l10n_in_edi_generate_invoice_json_managing_negative_lines(json_payload)

    def _l10n_in_get_supply_type(self, is_igst_amount):
        if self.l10n_in_gst_treatment in ("overseas", "special_economic_zone") and is_igst_amount:
            return {
                'overseas': 'EXPWP',
                'special_economic_zone': 'SEZWP',
            }[self.l10n_in_gst_treatment]
        return {
            'deemed_export': 'DEXP',
            'overseas': 'EXPWOP',
            'special_economic_zone': 'SEZWOP',
        }.get(self.l10n_in_gst_treatment, 'B2B')

    # ================= Get Error =================
    def _l10n_in_check_einvoice_validation(self):
        alerts = {
            **self.company_id._l10n_in_check_einvoice_validation(),
            **(self.partner_id | self.partner_shipping_id)._l10n_in_check_einvoice_validation(),
            **self.invoice_line_ids._l10n_in_check_einvoice_validation(),
        }
        if invalid_records := self.filtered(lambda m: not re.match("^.{1,16}$", m.name)):
            alerts['l10n_in_edi_invalid_invoice_number'] = {
                'message': _("Invoice number should not be more than 16 characters"),
                'action_text': _("View Invoices"),
                'action': invalid_records._get_records_action(name=_("Check Invoices")),
            }
        return alerts

    # ------Utils------
    @api.model
    def _get_l10n_in_gst_tags(self):
        return [
            self.env['ir.model.data']._xmlid_to_res_id(f'l10n_in.tax_tag_{xmlid}')
            for xmlid in (
                'base_sgst',
                'base_cgst',
                'base_igst',
                'base_cess',
                'zero_rated'
            )
        ]

    @api.model
    def _get_l10n_in_non_taxable_tags(self):
        return [
            self.env['ir.model.data']._xmlid_to_res_id(f'l10n_in.tax_tag_{xmlid}')
            for xmlid in (
                'exempt',
                'nil_rated',
                'non_gst_supplies'
            )
        ]

    # ================================ API methods ===========================
    def _l10n_in_edi_connect_to_server(self, url_end_point, json_payload=False, params=False):
        """
        url_end_point possible values (generate, getirnbydocdetails, generate_ewaybill_by_irn, get_ewaybill_by_irn, cancel)
        is used to get the EDI response from the server
        """
        company = self.company_id
        token = company._l10n_in_edi_get_token()
        if not token:
            return {
                'error': [{
                    'code': '0',
                    'message': _(
                        "Ensure GST Number set on company setting and API are Verified."
                    )
                }]
            }
        default_params = {
            'auth_token': token,
            'username': company.sudo().l10n_in_edi_username,
            'gstin': company.vat,
        }
        if params:
            # To be used when generate_ewaybill_by_irn, get_ewaybill_by_irn
            params.update(default_params)
        else:
            params = {
                **default_params,
                'json_payload': json_payload
            }
        try:
            response = self.env['iap.account']._l10n_in_connect_to_server(
                company.sudo().l10n_in_edi_production_env,
                params,
                f"/iap/l10n_in_edi/1/{url_end_point}",
                'l10n_in_edi.endpoint'
            )
        except AccessError as e:
            _logger.warning("Connection error: %s", e.args[0])
            return {
                'error': [{
                    'code': '404',
                    'message': _(
                        "Unable to connect to the online E-invoice service."
                        "The web service may be temporary down. Please try again in a moment."
                    )
                }]
            }
        if (error := response.get('error')) and '1005' in [e.get("code") for e in error]:
            # Invalid token eror then create new token and send generate request again.
            # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
            authenticate_response = company._l10n_in_edi_authenticate()
            if not authenticate_response.get("error"):
                response = self._l10n_in_edi_connect_to_server(
                    url_end_point=url_end_point,
                    json_payload=json_payload,
                    params=params
                )
            else:
                return authenticate_response
        return response
