# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re
import base64
import pytz
from datetime import datetime
from collections import defaultdict
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_escape

from odoo.addons.l10n_in_ewaybill_stock.tools.ewaybill_api import EWayBillApi


class Ewaybill(models.Model):
    _name = "l10n.in.ewaybill"
    _description = "e-Waybill"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    # Ewaybill details generated from the API
    name = fields.Char("e-Way bill Number", copy=False, readonly=True)
    ewaybill_date = fields.Date("e-Way bill Date", copy=False, readonly=True)
    ewaybill_expiry_date = fields.Date("e-Way bill Valid Upto", copy=False, readonly=True)

    state = fields.Selection(string='Status', selection=[
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('cancel', 'Cancelled'),
    ], required=True, readonly=True, copy=False, tracking=True, default='pending')

    # Stock picking details
    stock_picking_id = fields.Many2one("stock.picking", "Stock Transfer", copy=False)
    move_ids = fields.One2many(comodel_name='stock.move', related="stock_picking_id.move_ids", inverse_name='ewaybill_id', store=True)
    picking_type_code = fields.Selection(related='stock_picking_id.picking_type_id.code')

    # Document details
    document_date = fields.Datetime("Document Date", compute="_compute_document_details", store=True)
    document_number = fields.Char("Document", compute="_compute_document_details", store=True)
    company_id = fields.Many2one("res.company", compute="_compute_document_details", store=True)
    supply_type = fields.Selection(string="Supply Type", selection=[
        ("O", "Outward"),
        ("I", "Inward")
    ], compute="_compute_supply_type")
    partner_bill_to_id = fields.Many2one("res.partner", string='Bill To', compute="_compute_document_partners_details", store=True, readonly=False)
    partner_bill_from_id = fields.Many2one("res.partner", string='Bill From', compute="_compute_document_partners_details", store=True, readonly=False)
    partner_ship_to_id = fields.Many2one('res.partner', string='Ship To', compute='_compute_document_partners_details', store=True, readonly=False)
    partner_ship_from_id = fields.Many2one("res.partner", string='Ship From', compute="_compute_document_partners_details", store=True, readonly=False)

    # Fields to determine which partner details are editable
    is_bill_to_editable = fields.Boolean(compute="_compute_is_editable")
    is_bill_from_editable = fields.Boolean(compute="_compute_is_editable")
    is_ship_to_editable = fields.Boolean(compute="_compute_is_editable")
    is_ship_from_editable = fields.Boolean(compute="_compute_is_editable")

    transaction_type = fields.Selection(
        selection=[
            ("inter_state", "Inter State"),
            ("intra_state", "Intra State"),
        ],
        string="Transaction",
        compute="_compute_transaction_type",
        readonly=False,
        required=True
    )

    # E-waybill Document Type
    type_id = fields.Many2one("l10n.in.ewaybill.type", "E-waybill Document Type", tracking=True, required=True)
    sub_type_code = fields.Char(related="type_id.sub_type_code")
    type_description = fields.Char(string="Description")

    # Transportation details
    distance = fields.Integer("Distance", tracking=True)
    mode = fields.Selection([
        ("0", "Managed by Transporter"),
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship")
    ], string="Transportation Mode", copy=False, tracking=True, required=True)

    # Vehicle Number and Type required when transportation mode is By Road.
    vehicle_no = fields.Char("Vehicle Number", copy=False, tracking=True)
    vehicle_type = fields.Selection([
        ("R", "Regular"),
        ("O", "ODC")],
        string="Vehicle Type", copy=False, tracking=True)

    # Document number and date required in case of transportation mode is Rail, Air or Ship.
    transportation_doc_no = fields.Char(
        string="Transporter's Doc No",
        help="""Transport document number. If it is more than 15 chars, last 15 chars may be entered""",
        copy=False, tracking=True)
    transportation_doc_date = fields.Date(
        string="Transporter's Doc Date",
        help="Date on the transporter document",
        copy=False,
        tracking=True)

    transporter_id = fields.Many2one("res.partner", "Transporter", copy=False, tracking=True)

    error_message = fields.Html(readonly=True)
    blocking_level = fields.Selection([
        ("warning", "Warning"),
        ("error", "Error")],
        string="Blocking Level", readonly=True)

    content = fields.Binary(compute='_compute_content', compute_sudo=True)
    cancel_reason = fields.Selection(selection=[
        ("1", "Duplicate"),
        ("2", "Data Entry Mistake"),
        ("3", "Order Cancelled"),
        ("4", "Others"),
    ], string="Cancel reason", copy=False, tracking=True)
    cancel_remarks = fields.Char("Cancel remarks", copy=False, tracking=True)

    def _compute_supply_type(self):
        for ewaybill in self:
            ewaybill.supply_type = 'I' if ewaybill.picking_type_code == 'incoming' else 'O'

    @api.depends('partner_bill_to_id', 'partner_bill_from_id')
    def _compute_document_details(self):
        for ewaybill in self:
            stock_picking_id = ewaybill.stock_picking_id
            ewaybill.document_number = stock_picking_id.name
            ewaybill.company_id = stock_picking_id.company_id.id
            ewaybill.document_date = stock_picking_id.date_done or stock_picking_id.scheduled_date

    @api.depends('stock_picking_id')
    def _compute_document_partners_details(self):
        for ewaybill in self:
            stock_picking_id = ewaybill.stock_picking_id
            if ewaybill.picking_type_code == 'incoming':
                ewaybill.partner_bill_to_id = stock_picking_id.company_id.partner_id
                ewaybill.partner_bill_from_id = stock_picking_id.partner_id
                ewaybill.partner_ship_to_id = stock_picking_id.picking_type_id.warehouse_id.partner_id
                ewaybill.partner_ship_from_id = stock_picking_id.partner_id
            else:
                ewaybill.partner_bill_to_id = stock_picking_id.partner_id
                ewaybill.partner_bill_from_id = stock_picking_id.company_id.partner_id
                ewaybill.partner_ship_to_id = stock_picking_id.partner_id
                ewaybill.partner_ship_from_id = stock_picking_id.picking_type_id.warehouse_id.partner_id

    @api.depends('partner_bill_from_id', 'partner_bill_to_id')
    def _compute_transaction_type(self):
        for ewaybill in self:
            if ewaybill.partner_bill_from_id.state_id == ewaybill.partner_bill_to_id.state_id:
                ewaybill.transaction_type = 'intra_state'
            else:
                ewaybill.transaction_type = 'inter_state'

    @api.depends('partner_ship_from_id', 'partner_ship_to_id', 'partner_bill_from_id', 'partner_bill_to_id')
    def _compute_is_editable(self):
        for ewaybill in self:
            is_incoming = ewaybill.picking_type_code == "incoming"
            ewaybill.is_bill_to_editable = not is_incoming
            ewaybill.is_bill_from_editable = is_incoming
            ewaybill.is_ship_from_editable = is_incoming and ewaybill._is_overseas()
            ewaybill.is_ship_to_editable = not is_incoming and not ewaybill._is_overseas()

    def _compute_content(self):
        for ewaybill in self:
            ewaybill.content = base64.b64encode(json.dumps(ewaybill._ewaybill_generate_direct_json()).encode())

    @api.depends('name', 'state')
    def _compute_display_name(self):
        for ewaybill in self:
            ewaybill.display_name = ewaybill.name or _('Pending')

    def action_export_json(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/l10n.in.ewaybill/%s/content' % self.id
        }

    def generate_ewaybill(self):
        for ewaybill in self:
            errors = ewaybill._check_ewaybill_configuration()
            if errors:
                raise UserError('\n'.join(errors))
            ewaybill._generate_ewaybill_direct()

    def cancel_ewaybill(self):
        self.ensure_one()
        return {
            'name': _('Cancel Ewaybill'),
            'res_model': 'l10n.in.ewaybill.cancel',
            'view_mode': 'form',
            'context': {
                'default_ewaybill_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _is_overseas(self):
        self.ensure_one()
        gst_treatment = self._get_gst_treatment()
        if gst_treatment in ('overseas', 'special_economic_zone'):
            return True
        return False

    def _check_ewaybill_configuration(self):
        error_message = []
        methods_to_check = [self._check_ewaybill_partners, self._check_ewaybill_document_number, self._check_lines, self._check_gst_customer_treatment]
        if self.mode == '0':
            error_message += self._check_ewaybill_transporter()
        for get_error_message in methods_to_check:
            error_message.extend(get_error_message())
        return error_message

    def _check_ewaybill_transporter(self):
        if self.transporter_id and not self.transporter_id.vat:
            return [_("- Transporter %s does not have GST Number", self.transporter_id.name)]
        return []

    def _check_ewaybill_partners(self):
        error_message = []
        partners = {self.partner_bill_to_id, self.partner_bill_from_id, self.partner_ship_to_id, self.partner_ship_from_id}
        for partner in partners:
            error_message += self._l10n_in_validate_partner(partner)
        return error_message

    @api.model
    def _l10n_in_validate_partner(self, partner, is_company=False):
        message = []
        if partner.country_id.code == "IN":
            if not partner.state_id.l10n_in_tin:
                message.append(_("- State with TIN number is required"))
            if not partner.zip or not re.match("^[0-9]{6}$", partner.zip):
                message.append(_("- Zip code required and should be 6 digits"))
        if message:
            message.insert(0, "%s" % (partner.display_name))
        return message

    def _check_ewaybill_document_number(self):
        if not re.match("^.{1,16}$", self.document_number):
            return [_("Document number should be set and not more than 16 characters")]
        return []

    def _check_lines(self):
        error_message = []
        for line in self.move_ids:
            hsn_code = self._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code)
            if not hsn_code:
                error_message.append(_("HSN code is not set in product %s", line.product_id.name))
            elif not re.match("^[0-9]+$", hsn_code):
                error_message.append(_(
                    "Invalid HSN Code (%s) in product %s", hsn_code, line.product_id.name
                ))
        return error_message

    def _check_gst_customer_treatment(self):
        if not self._get_gst_treatment():
            return [_("Set GST Treatment for Partner")]
        return []

    def _get_gst_treatment(self):
        if self.picking_type_code == 'incoming':
            gst_treatment = self.partner_bill_from_id.l10n_in_gst_treatment
        else:
            gst_treatment = self.partner_bill_to_id.l10n_in_gst_treatment
        return gst_treatment

    def _write_error(self, error_message, blocking_level='error'):
        self.write({
            'error_message': error_message,
            'blocking_level': blocking_level,
        })

    def _write_successfully_response(self, response_vals):
        response_vals.update({
            'error_message': False,
            'blocking_level': False,
        })
        self.write(response_vals)

    def _ewaybill_cancel(self):
        cancel_json = {
            "ewbNo": int(self.name),
            "cancelRsnCode": int(self.cancel_reason),
            "CnlRem": self.cancel_remarks,
        }
        ewb_api = EWayBillApi(self.company_id)
        response = ewb_api._ewaybill_cancel(cancel_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happens when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = ewb_api._ewaybill_authenticate()
                if not authenticate_response.get("error"):
                    error = []
                    response = ewb_api._ewaybill_cancel(cancel_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "312" in error_codes:
                # E-waybill is already canceled
                # this happens when timeout from the Government portal but IRN is generated
                error_message = Markup("<br/>").join([Markup("[%s] %s") % (
                e.get("code"), e.get("message")) for e in error])
                error = []
                response = {"data": ""}
                odoobot = self.env.ref("base.partner_root")
                self.message_post(author_id=odoobot.id, body=
                Markup("%s<br/>%s:<br/>%s") % (
                    _("Somehow this E-waybill has been canceled in the government portal before. You can verify by checking the details into the government (https://ewaybillgst.gov.in/Others/EBPrintnew.asp)"),
                    _("Error"),
                    error_message
                ))
            if "no-credit" in error_codes:
                error_message = self._l10n_in_edi_get_iap_buy_credits_message(self.company_id)
                self._write_error(error_message)
            elif error:
                error_message = Markup("<br/>").join([Markup("[%s] %s") % (
                e.get("code"), e.get("message")) for e in error])
                blocking_level = "error"
                if "404" in error_codes:
                    blocking_level = "warning"
                self._write_error(error_message, blocking_level)
        # Not use else because we re-send request in case of invalid token error
        if not response.get("error"):
            self._write_successfully_response({'state': 'cancel'})

    def _generate_ewaybill_direct(self):
        ewb_api = EWayBillApi(self.company_id)
        generate_json = self._ewaybill_generate_direct_json()
        response = ewb_api._ewaybill_generate(generate_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happens when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = ewb_api._ewaybill_authenticate()
                if not authenticate_response.get("error"):
                    error = []
                    response = ewb_api._ewaybill_generate(generate_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "604" in error_codes:
                # Get E-waybill by details in case of E-waybill is already generated
                # this happens when timeout from the Government portal but E-waybill is generated
                response = ewb_api._ewaybill_get_by_consigner(generate_json.get("docType"), generate_json.get("docNo"))
                if not response.get("error"):
                    error = []
                    odoobot = self.env.ref("base.partner_root")
                    self.message_post(author_id=odoobot.id, body=
                    _("Somehow this E-waybill has been generated in the government portal before. You can verify by checking the invoice details into the government (https://ewaybillgst.gov.in/Others/EBPrintnew.asp)")
                                      )
            if "no-credit" in error_codes:
                error_message = self._l10n_in_edi_get_iap_buy_credits_message(self.company_id)
                self._write_error(error_message)
            elif error:
                error_message = "<br/>".join([
                    "[%s] %s" % (
                        e.get("code"),
                        html_escape(e.get("message"))
                    )
                for e in error])
                blocking_level = "error"
                if "404" in error_codes:
                    blocking_level = "warning"
                self._write_error(error_message, blocking_level)
        # Not use else because we re-send request in case of invalid token error
        if not response.get("error"):
            self.state = 'generated'
            response_data = response.get("data")
            self._write_successfully_response({
                'name': response_data.get("ewayBillNo"),
                'ewaybill_date': self._indian_timezone_to_odoo_utc(response_data.get('ewayBillDate'), '%d/%m/%Y %I:%M:%S %p'),
                'ewaybill_expiry_date': self._indian_timezone_to_odoo_utc(response_data.get('validUpto'), '%d/%m/%Y %I:%M:%S %p'),
            })

    @api.model
    def _l10n_in_edi_get_iap_buy_credits_message(self, company):
        url = self.env["iap.account"].get_credits_url(service_name="l10n_in_edi")
        return Markup("""<p><b>%s</b></p><p>%s <a href="%s">%s</a></p>""") % (
            _("You have insufficient credits to send this document!"),
            _("Please buy more credits and retry: "),
            url,
            _("Buy Credits")
        )

    @api.model
    def _indian_timezone_to_odoo_utc(self, str_date, time_format="%Y-%m-%d %H:%M:%S"):
        """
            This method is used to convert date from Indian timezone to UTC
        """
        local_time = datetime.strptime(str_date, time_format)
        utc_time = local_time.astimezone(pytz.utc)
        return fields.Datetime.to_string(utc_time)

    @api.model
    def _get_partner_state_code(self, partner):
        return int(partner.state_id.l10n_in_tin) if partner.country_id.code == "IN" else 99

    @api.model
    def _get_partner_zip(self, partner):
        return int(partner.zip) if partner.country_id.code == "IN" else 999999

    @api.model
    def _get_partner_gst_number(self, partner):
        return partner.commercial_partner_id.vat or "URP"

    @api.model
    def _get_partner_ship_address(self, partner):
        address = ''.join(addr for addr in partner if addr.isalnum() or addr.isspace() or addr in '#-/')[:120]
        return address

    @api.model
    def _l10n_in_edi_extract_digits(self, string):
        if not string:
            return string
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

    @api.model
    def _l10n_in_round_value(self, amount, precision_digits=2):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        value = round(amount, precision_digits)
        # avoid -0.0
        return value if value else 0.0

    @api.model
    def _l10n_in_tax_details(self, ewaybill):
        tax_details = {'line_tax_details': defaultdict(dict), 'tax_details':defaultdict(float)}
        for move in ewaybill.move_ids:
            line_tax_vals = self._l10n_in_tax_details_by_line(move)
            tax_details['line_tax_details'][move.id] = line_tax_vals
            tax_details['tax_details']['total_excluded'] += line_tax_vals['total_excluded']
            tax_details['tax_details']['total_included'] += line_tax_vals['total_included']
            tax_details['tax_details']['total_void'] += line_tax_vals['total_void']
            for tax in ['igst', 'cgst', 'sgst', 'cess_non_advol', 'cess', 'other']:
                for taxes in line_tax_vals['taxes']:
                    rate_key = "%s_rate" % (tax)
                    amount_key = "%s_amount" % (tax)
                    if rate_key in taxes:
                        tax_details['tax_details'][rate_key] += taxes[rate_key]
                    if amount_key in taxes:
                        tax_details['tax_details'][amount_key] += taxes[amount_key]
        return tax_details

    def _l10n_in_tax_details_by_line(self, move):
        taxes = move.ewaybill_tax_ids.compute_all(price_unit=move.ewaybill_price_unit, quantity=move.quantity)
        tax_vals = {}
        for tax in taxes['taxes']:
            tax_id = self.env['account.tax'].browse(tax['id'])
            tax_name = "other"
            for gst_tax_name in ['igst', 'sgst', 'cgst']:
                if self.env.ref("l10n_in.tax_tag_%s" % (gst_tax_name)).id in tax['tag_ids']:
                    tax_name = gst_tax_name
            if self.env.ref("l10n_in.tax_tag_cess").id in tax['tag_ids']:
                tax_name = tax_id.amount_type != "percent" and "cess_non_advol" or "cess"
            rate_key = "%s_rate" % (tax_name)
            amount_key = "%s_amount" % (tax_name)
            tax.setdefault(rate_key, 0)
            tax.setdefault(amount_key, 0)
            tax[rate_key] += tax_id.amount
            tax[amount_key] += tax['amount']
        return taxes

    def _get_l10n_in_ewaybill_line_details(self, line, tax_details):
        round_value = self._l10n_in_round_value
        line_details = {
            "productName": line.product_id.name,
            "hsnCode": self._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code),
            "productDesc": line.product_id.name,
            "quantity": line.quantity,
            "qtyUnit": line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split("-")[
                0] or "OTH",
            "taxableAmount": round_value(line.ewaybill_price_unit),
        }
        if tax_details.get('igst_rate'):
            line_details.update({"igstRate": round_value(tax_details.get("igst_rate", 0.00))})
        else:
            line_details.update({
                "cgstRate": round_value(tax_details.get("cgst_rate", 0.00)),
                "sgstRate": round_value(tax_details.get("sgst_rate", 0.00)),
            })
        if tax_details.get("cess_rate"):
            line_details.update({"cessRate": round_value(tax_details.get("cess_rate", 0.00))})
        return line_details

    def _ewaybill_generate_direct_json(self):
        for ewaybill in self:
            def get_transaction_type(seller_details, dispatch_details, buyer_details, ship_to_details):
                """
                    1 - Regular
                    2 - Bill To - Ship To
                    3 - Bill From - Dispatch From
                    4 - Combination of 2 and 3
                """
                if seller_details != dispatch_details and buyer_details != ship_to_details:
                    return 4
                elif seller_details != dispatch_details:
                    return 3
                elif buyer_details != ship_to_details:
                    return 2
                else:
                    return 1

            partner_bill_to_id = self.partner_bill_to_id
            partner_bill_from_id = self.partner_bill_from_id
            partner_ship_to_id = self.partner_ship_to_id
            partner_ship_from_id = self.partner_ship_from_id
            json_payload = {
                # document details
                "supplyType": self.supply_type,
                "subSupplyType": self.type_id.sub_type_code,
                "docType": self.type_id.code,
                "transactionType": get_transaction_type(partner_bill_from_id, partner_ship_from_id, partner_bill_to_id, partner_ship_to_id),
                "transDistance": str(self.distance),
                "docNo": self.document_number,
                "docDate": self.document_date.strftime("%d/%m/%Y"),
                # Bill from
                "fromGstin": self._get_partner_gst_number(partner_bill_from_id),
                "fromTrdName": partner_bill_from_id.commercial_partner_id.name,
                "fromStateCode": self._get_partner_state_code(partner_bill_from_id),
                # Ship from
                "fromAddr1": partner_ship_from_id.street and self._get_partner_ship_address(partner_ship_from_id.street) or "",
                "fromAddr2": partner_ship_from_id.street2 and self._get_partner_ship_address(partner_ship_from_id.street2) or "",
                "fromPlace": partner_ship_from_id.city if partner_ship_from_id.city and len(partner_ship_from_id.city) <= 50 else "",
                "fromPincode": self._get_partner_zip(partner_ship_from_id),
                "actFromStateCode": self._get_partner_state_code(partner_ship_from_id),
                # Bill to
                "toGstin": self._get_partner_gst_number(partner_bill_to_id),
                "toTrdName": partner_bill_to_id.commercial_partner_id.name,
                "actToStateCode": self._get_partner_state_code(partner_bill_to_id),
                # Ship to
                "toAddr1": partner_ship_to_id.street and self._get_partner_ship_address(partner_ship_to_id.street) or "",
                "toAddr2": partner_ship_to_id.street2 and self._get_partner_ship_address(partner_ship_to_id.street2) or "",
                "toPlace": partner_ship_to_id.city if partner_ship_to_id.city and len(partner_ship_to_id.city) <= 50 else "",
                "toStateCode": self._get_partner_state_code(partner_ship_to_id),
                "toPincode": self._get_partner_zip(partner_ship_to_id),
            }
            if self.sub_type_code == '8':
                json_payload.update({
                    "subSupplyDesc": self.type_description,
                })
            if self.mode == "0":
                json_payload.update({
                    "transporterId": self.transporter_id.vat,
                    "transporterName": self.transporter_id.name or "",
                })
            elif self.mode in ("2", "3", "4"):
                json_payload.update({
                    "transMode": self.mode,
                    "transDocNo": self.transportation_doc_no,
                    "transDocDate": self.transportation_doc_date.strftime("%d/%m/%Y"),
                })
            elif self.mode == "1":
                json_payload.update({
                    "transMode": self.mode,
                    "vehicleNo": self.vehicle_no,
                    "vehicleType": self.vehicle_type,
                })
            tax_details = self._l10n_in_tax_details(ewaybill)
            round_value = self._l10n_in_round_value
            json_payload.update({
                "itemList": [
                    self._get_l10n_in_ewaybill_line_details(line, tax_details['line_tax_details'][line.id])
                    for line in ewaybill.move_ids
                ],
                "totalValue": round_value(tax_details['tax_details'].get('total_excluded', 0.00)),
                "cgstValue": round_value(tax_details.get('cgst_amount', 0.00)),
                "sgstValue": round_value(tax_details.get('sgst_amount', 0.00)),
                "igstValue": round_value(tax_details.get('igst_amount', 0.00)),
                "cessValue": round_value(tax_details.get('cess_amount', 0.00)),
                "cessNonAdvolValue": round_value(tax_details.get('cess_non_advol_amount', 0.00)),
                "otherValue": round_value(tax_details.get('other_amount', 0.00)),
                "totInvValue": round_value(tax_details['tax_details'].get('total_included', 0.00)),
            })
            return json_payload

    @api.ondelete(at_uninstall=False)
    def _unlink_l10n_in_ewaybill_prevent(self):
        for ewaybill in self:
            if ewaybill.state != 'pending':
                raise UserError(_("You cannot delete a generated E-waybill. Instead, you should cancel it."))
