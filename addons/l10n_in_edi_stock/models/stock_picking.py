# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import markupsafe
import json
import pytz
import re

from datetime import datetime, timedelta
from psycopg2 import OperationalError

from odoo import _, api, fields, models
from odoo.addons.iap import jsonrpc
from odoo.exceptions import AccessError, UserError
from odoo.tools import html_escape
import logging

_logger = logging.getLogger(__name__)

# TODO: change DEFAULT_IAP_ENDPOINT
DEFAULT_IAP_ENDPOINT = "https://ewaybill-sandbox2.odoo.com"
DEFAULT_IAP_TEST_ENDPOINT = "https://ewaybill-sandbox2.odoo.com"


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_in_fiscal_position_id = fields.Many2one('account.fiscal.position',
        string="Fiscal Position",
        help="The fiscal position determines the taxes/accounts used for this contact.")
    l10n_in_edi_stock_state = fields.Selection(
        [
            ('to_send', "To Send"),
            ("send", "Send"),
            ("to_cancel", "To Cancel"),
            ("cancelled", "Cancelled"),
        ],
        string="E-Waybill Status",
        copy=False,
        readonly=True,
        tracking=True,
    )

    # Transaction Details
    l10n_in_transaction_type = fields.Selection(
        [
            ("1", "Regular"),
            ("2", "Bill To-Ship To"),
            ("3", "Bill From-Dispatch From"),
            ("4", "Combination of 2 and 3"),
        ],
        string="Transaction Type",
        copy=False
    )
    l10n_in_type_id = fields.Many2one("l10n.in.ewaybill.type", "Document Type")
    l10n_in_subtype_id = fields.Many2one("l10n.in.ewaybill.type", "Sub Supply Type")
    l10n_in_sub_supply_desc = fields.Char("Sub Supply Description")

    # Transportation Details
    l10n_in_mode = fields.Selection(
        [
            ("0", "Managed by Transporter"),
            ("1", "By Road"),
            ("2", "Rail"),
            ("3", "Air"),
            ("4", "Ship"),
        ],
        string="Transportation Mode",
        copy=False
    )
    l10n_in_vehicle_type = fields.Selection(
        [
            ("R", "Regular"),
            ("O", "ODC"),
        ],
        string="Vehicle Type",
        copy=False
    )
    l10n_in_transporter_id = fields.Many2one("res.partner", "Transporter", copy=False)
    l10n_in_distance = fields.Integer("Distance", copy=False)
    l10n_in_vehicle_no = fields.Char("Vehicle Number", copy=False)
    l10n_in_transporter_doc_no = fields.Char(
        "Document Number",
        help="""Transport document number.
If it is more than 15 chars, last 15 chars may be entered""", copy=False
    )
    l10n_in_transporter_doc_date = fields.Date("Document Date", help="Date on the transporter document", copy=False)

    # E-WayBill Details
    l10n_in_ewaybill_number = fields.Char("EWaybill Number", tracking=True, readonly=True, copy=False)
    l10n_in_ewaybill_valid_upto = fields.Datetime("EWaybill Valid Upto", tracking=True, readonly=True, copy=False)
    l10n_in_edi_error_message = fields.Html(
        help='The text of the last error that happened during E-WayBill operation.',
        readonly=True,
        copy=False
    )
    l10n_in_edi_blocking_level = fields.Selection(selection=[('warning', 'Warning'), ('error', 'Error')], copy=False)

    # E-Waybill cancel
    l10n_in_edi_cancel_reason_code = fields.Selection(
        [
            ("1", "Duplicate"),
            ("2", "Order Cancelled"),
            ("3", "Data Entry mistake"),
            ("4", "Others"),
        ],
        "Cancel Reason",
        copy=False
    )
    l10n_in_edi_cancel_remark = fields.Char("Cancel Remark", copy=False)

    @api.onchange('l10n_in_type_id')
    def _onchange_l10n_in_type_id(self):
        self.l10n_in_subtype_id = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.l10n_in_fiscal_position_id = self.partner_id.property_account_position_id

    def button_l10n_in_send_ewaybill(self):
        self.ensure_one()
        self._l10n_in_edi_ewaybill_check_configuration()
        self.l10n_in_edi_stock_state = "to_send"
        self.env.ref('l10n_in_edi_stock.ir_cron_l10n_in_edi_stock_web_services')._trigger()

    def button_l10n_in_cancel_ewaybill(self):
        self.ensure_one()
        if not self.l10n_in_edi_cancel_reason_code:
            raise UserError(_("Cancel Reason is required."))
        self.l10n_in_edi_stock_state = "to_cancel"
        self.env.ref('l10n_in_edi_stock.ir_cron_l10n_in_edi_stock_web_services')._trigger()

    def button_l10n_in_extend_ewaybill(self):
        self.ensure_one()
        context = self.env.context.copy()
        context.update({"picking_id": self.id, "default_request_type": "extend"})
        return {
            "name": _("Extend EWaybill"),
            "res_model": "l10n.in.edi.stock.extend.update.partb",
            "view_mode": "form",
            "view_id": self.env.ref("l10n_in_edi_stock.view_extend_or_update_part_b").id,
            "target": "new",
            "type": "ir.actions.act_window",
            "context": context,
        }

    def button_l10n_in_update_part_b(self):
        self.ensure_one()
        context = self.env.context.copy()
        context.update({"picking_id": self.id, "default_request_type": "update_part_b"})
        return {
            "name": _("Update Part-B"),
            "res_model": "l10n.in.edi.stock.extend.update.partb",
            "view_mode": "form",
            "view_id": self.env.ref("l10n_in_edi_stock.view_extend_or_update_part_b").id,
            "target": "new",
            "type": "ir.actions.act_window",
            "context": context,
        }

    def button_l10n_in_update_transporter(self):
        self.ensure_one()
        context = self.env.context.copy()
        context.update({"picking_id": self.id, "default_request_type": "update_transporter"})
        return {
            "name": _("Update Transporter ID"),
            "res_model": "l10n.in.edi.stock.extend.update.partb",
            "view_mode": "form",
            "view_id": self.env.ref("l10n_in_edi_stock.view_extend_or_update_part_b").id,
            "target": "new",
            "type": "ir.actions.act_window",
            "context": context,
        }

    def button_retry_l10n_in_edi_stock(self):
        self._l10n_in_edi_ewaybill_check_configuration()
        self.process_l10n_in_edi_stock()

    @api.model
    def _cron_process_l10n_in_edi_web_services(self, job_count=None):
        all_jobs = self.search([
            ('l10n_in_edi_stock_state', 'in', ('to_send', 'to_cancel')),
            ('l10n_in_edi_blocking_level', '!=', 'error')
        ])
        remaining_jobs = all_jobs.process_l10n_in_edi_stock(job_count=job_count)
        if remaining_jobs > 0:
            self.env.ref('l10n_in_edi_stock.ir_cron_l10n_in_edi_stock_web_services')._trigger()

    def _l10n_in_edi_stock_get_iap_buy_credits_message(self, company):
        base_url = "https://iap-sandbox.odoo.com/iap/1/credit" if not company.sudo().l10n_in_edi_stock_production_env else ""
        url = self.env["iap.account"].get_credits_url(service_name="l10n_in_edi", base_url=base_url)
        return markupsafe.Markup("""<p><b>%s</b></p><p>%s</p>""" % (
            _("You have insufficient credits to send this document!"),
            _("Please proceed to buy more credits <a href='%s'>here.</a>", url),
        ))

    def process_l10n_in_edi_stock(self, job_count=None):
        jobs_to_process = self[0:job_count] if job_count else self
        for picking in jobs_to_process:
            try:
                with self.env.cr.savepoint(flush=False):
                    self._cr.execute('SELECT * FROM stock_picking WHERE id IN %s FOR UPDATE NOWAIT',
                        [tuple(picking.ids)])
            except OperationalError as e:
                if e.pgcode == '55P03':
                    _logger.debug('Another transaction already locked Transfers rows. Cannot process E-Waybill.')
                    continue
                else:
                    raise e
            if picking.l10n_in_edi_stock_state == "to_send":
                picking._process_l10n_in_edi_stock_send()
            elif picking.l10n_in_edi_stock_state == "to_cancel":
                picking._process_l10n_in_edi_stock_cancel()
            if len(jobs_to_process) > 1:
                self.env.cr.commit()
        return len(self) - len(jobs_to_process)

    def _process_l10n_in_edi_stock_send(self):
        json_payload = self._l10n_in_edi_stock_prepare_json()
        response = self._l10n_in_edi_stock_submit(self.company_id, json_payload)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                authenticate_response = self._l10n_in_edi_stock_authenticate(self.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_stock_submit(self.company_id, json_payload)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "604" in error_codes:
                get_ewaybill_response = self._get_l10n_in_edi_stock_details_by_consigner(
                    self.company_id, json_payload.get('docType'), json_payload.get('docNo'))
                if not get_ewaybill_response.get("error"):
                    response = get_ewaybill_response
                    error_codes = []
                    error = []
                    odoobot = self.env.ref("base.partner_root")
                    self.message_post(author_id=odoobot.id, body=_(
                        "Somehow this ewaybill had been submited to government before." \
                        "<br/>Normally, this should not happen too often" \
                        "<br/>Just verify value of ewaybill by fillup details on government website " \
                        "<a href='https://ewaybill2.nic.in/ewaybill_nat2/Others/EBPrintnew.aspx'>here<a>."
                    ))
            if "no-credit" in error_codes:
                self.write({
                    "l10n_in_edi_error_message": self._l10n_in_edi_stock_get_iap_buy_credits_message(self.company_id),
                    "l10n_in_edi_blocking_level": "error",
                })
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                self.write({
                    "l10n_in_edi_error_message": error_message,
                    "l10n_in_edi_blocking_level": ("404" in error_codes) and "warning" or "error",
                })
        if not response.get("error"):
            response_data = response.get("data", {})
            json_dump = json.dumps(response_data)
            json_name = "%s_ewaybill_%s.json" % (
                self.name.replace("/", "_"), fields.Datetime.now().strftime('%d_%m_%y_%H_%M_%S'))
            self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "stock.picking",
                "res_id": self.id,
                "mimetype": "application/json",
            })
            utc_time = False
            if response_data.get("validUpto"):
                # validUpto not send when transport by other party (when set transporter)
                tz = pytz.timezone("Asia/Kolkata")
                datetime_formate = "%d/%m/%Y %H:%M:%S %p"
                if len(response_data["validUpto"]) == 20:
                    datetime_formate = "%d/%m/%Y %H:%M:%S "
                local_time = tz.localize(datetime.strptime(response_data["validUpto"], datetime_formate))
                utc_time = local_time.astimezone(pytz.utc)
            self.write({
                'l10n_in_edi_error_message': False,
                'l10n_in_edi_blocking_level': False,
                'l10n_in_edi_cancel_reason_code': False,
                'l10n_in_edi_cancel_remark': False,
                'l10n_in_edi_stock_state': 'send',
                'l10n_in_ewaybill_number': response_data.get('ewayBillNo'),
                'l10n_in_ewaybill_valid_upto': fields.Datetime.to_string(utc_time),
            })
            odoobot = self.env.ref("base.partner_root")
            self.message_post(author_id=odoobot.id, body=_(
                "Generated E-Waybill with Document Number %s and Document Date %s",
                json_payload.get('docNo'), json_payload.get('docDate')
            ))
            if response_data.get('alert'):
                self.message_post(author_id=odoobot.id, body=_('%s', response_data['alert']))

    def _process_l10n_in_edi_stock_cancel(self):
        json_payload = {
            'ewbNo': int(self.l10n_in_ewaybill_number),
            'cancelRsnCode': int(self.l10n_in_edi_cancel_reason_code),
        }
        if self.l10n_in_edi_cancel_remark:
            json_payload.update({'cancelRmrk': self.l10n_in_edi_cancel_remark})
        response = self._l10n_in_edi_stock_cancel(self.company_id, json_payload)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                authenticate_response = self._l10n_in_edi_stock_authenticate(self.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_stock_cancel(self.company_id, json_payload)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "no-credit" in error_codes:
                self.write({
                    "l10n_in_edi_error_message": self._l10n_in_edi_stock_get_iap_buy_credits_message(self.company_id),
                    "l10n_in_edi_blocking_level": "error",
                })
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                self.write({
                    "l10n_in_edi_error_message": error_message,
                    "l10n_in_edi_blocking_level": ("404" in error_codes) and "warning" or "error",
                })
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_cancel_ewaybill_%s.json" % (
                self.name.replace("/", "_"), fields.Datetime.now().strftime('%d_%m_%y_%H_%M_%S'))
            self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "stock.picking",
                "res_id": self.id,
                "mimetype": "application/json",
            })
            self.write({
                'l10n_in_edi_error_message': False,
                'l10n_in_edi_blocking_level': False,
                'l10n_in_edi_stock_state': 'cancelled',
                'l10n_in_ewaybill_number': False,
                'l10n_in_ewaybill_valid_upto': False,
            })

    def _l10n_in_edi_compare_stock_and_invoice(self):
        error_message = []
        product_qty = {}
        for stock_move_line in self.move_ids_without_package:
            product_qty.setdefault(stock_move_line.product_id, {'stock_qty': 0.00, 'invoice_qty': 0.00})
            product_qty[stock_move_line.product_id]['stock_qty'] += stock_move_line.quantity_done
        for account_move_line in self.l10n_in_related_invoice_id.invoice_line_ids.filtered(
            lambda line: not (line.display_type or line.is_rounding_line or line.product_id.type == 'service')):
            product_qty.setdefault(account_move_line.product_id, {'stock_qty': 0.00, 'invoice_qty': 0.00})
            product_qty[account_move_line.product_id]['invoice_qty'] += account_move_line.quantity
        for product_id, quantity in product_qty.items():
            if quantity.get('stock_qty') != quantity.get('invoice_qty'):
                error_message.append(_(
                    "- Product %s quantity is missmatch, Stock move quantity is %s and Related Invoiced quantity is %s.",
                    product_id.name, quantity.get('stock_qty'), quantity.get('invoice_qty'))
                )
        return error_message

    def _l10n_in_edi_check_require_fields(self, fields_name):
        self.ensure_one()
        error_message = []
        for field_name in fields_name:
            field = self.env["ir.model.fields"]._get(self._name, field_name)
            if field and not self[field_name]:
                error_message.append(_("- %s is Required.", field.field_description))
        return error_message

    def _l10n_in_edi_ewaybill_check_configuration(self):
        self.ensure_one()
        error_message = []
        required_fields = ['l10n_in_transaction_type', 'l10n_in_type_id', 'l10n_in_subtype_id', 'l10n_in_mode']
        if self.l10n_in_subtype_id == self.env.ref('l10n_in_edi_stock.type_others'):
            required_fields.append('l10n_in_sub_supply_desc')
        error_message += self._l10n_in_edi_check_require_fields(required_fields)
        if self.l10n_in_related_invoice_id:
            saler_buyer = self.env['account.edi.format']._get_l10n_in_edi_saler_buyer_party(
                self.l10n_in_related_invoice_id)
            error_message += self._l10n_in_edi_check_saler_buyer_party(saler_buyer)
            error_message += self._l10n_in_edi_compare_stock_and_invoice()
            error_message += self.l10n_in_related_invoice_id._l10n_in_edi_stock_validate_move()
        else:
            saler_buyer = self._get_l10n_in_edi_stock_saler_buyer_party()
            error_message += self._l10n_in_edi_check_saler_buyer_party(saler_buyer)
            error_message += self._l10n_in_edi_validate_picking()
        if error_message:
            raise UserError(_("Invalid E-Waybill configuration:\n\n%s", '\n'.join(error_message)))

    def _l10n_in_edi_check_saler_buyer_party(self, saler_buyer):
        if not saler_buyer:
            return []
        error_message = []
        dispatch_details = saler_buyer.get('dispatch_details')
        ship_to_details = saler_buyer.get('ship_to_details')
        seller_details = saler_buyer.get('seller_details')
        buyer_details = saler_buyer.get('buyer_details')
        error_message += self._l10n_in_edi_validate_partner(dispatch_details, "Ship From")
        error_message += self._l10n_in_edi_validate_partner(ship_to_details, "Ship To")
        only_self_gstin_type = self.env.ref('l10n_in_edi_stock.type_for_own_use') +\
            self.env.ref('l10n_in_edi_stock.type_line_sales') +\
            self.env.ref('l10n_in_edi_stock.type_recipient_unknown') +\
            self.env.ref('l10n_in_edi_stock.type_exhibition_of_fairs')
        if self.l10n_in_subtype_id in only_self_gstin_type and seller_details.vat != buyer_details.vat:
            error_message.append(_('- Sub Supply Type "%s" Need self GSTIN', self.l10n_in_subtype_id.name))
        return error_message

    @api.model
    def _l10n_in_edi_validate_partner(self, partner, prefix):
        error_message = []
        if not re.match("^.{3,100}$", partner.street or ""):
            error_message.append(_("- Street required min 3 and max 100 characters for %s", partner.name))
        if partner.street2 and not re.match("^.{3,100}$", partner.street2):
            error_message.append(_("- Street2 should be min 3 and max 100 characters for %s", partner.name))
        if not re.match("^.{3,100}$", partner.city or ""):
            error_message.append(_("- City required min 3 and max 100 characters for %s", partner.name))
        if partner and partner.country_id.code == "IN" and not re.match("^[0-9]{6,}$", partner.zip or ""):
            error_message.append(_("- %s(%s) required Pincode", prefix, partner.name))
        if partner and not partner.state_id:
            error_message.append(_("- %s(%s) required State", prefix, partner.name))
        return error_message

    def _l10n_in_edi_validate_picking(self):
        self.ensure_one()
        error_message = []
        if not re.match("^.{1,16}$", self.name):
            error_message.append(_("Picking number should not be more than 16 characters"))
        for line in self.move_ids_without_package:
            if line.product_id:
                hsn_code = self.env['account.edi.format']._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code)
                if not hsn_code:
                    error_message.append(_("- HSN code is not set in product %s", line.product_id.name))
                elif not re.match("^[0-9]+$", hsn_code):
                    error_message.append(_("- Invalid HSN Code (%s) in product %s", hsn_code, line.product_id.name))
            else:
                error_message.append(_("- product is required to get HSN code"))
        return error_message

    def _l10n_in_edi_stock_prepare_json(self):
        if self.l10n_in_related_invoice_id and self.l10n_in_type_id.code in ('INV', 'BIL', 'BOE'):
            json_payload = self.l10n_in_related_invoice_id._l10n_in_edi_stock_prepare_invoice_json()
        else:
            json_payload = self._l10n_in_edi_stock_prepare_stock_json()
        json_payload.update({
            "subSupplyType": self.l10n_in_subtype_id.code,
            "docType": self.l10n_in_type_id.code,
            "transactionType": int(self.l10n_in_transaction_type),
            "transDistance": str(self.l10n_in_distance or 0),
            'transMode': self.l10n_in_mode if self.l10n_in_mode != "0" else '',
            'transDocNo': self.l10n_in_transporter_doc_no if self.l10n_in_mode in ('2', '3', '4') else '',
            'vehicleNo': self.l10n_in_vehicle_no if self.l10n_in_mode == "1" else '',
        })
        if self.l10n_in_sub_supply_desc:
            json_payload.update({"subSupplyDesc": self.l10n_in_sub_supply_desc})
        if self.l10n_in_mode == '0':
            json_payload.update({'transporterId': self.l10n_in_transporter_id.vat})
        if self.l10n_in_mode == '0' and self.l10n_in_transporter_id:
            json_payload.update({'transporterName': self.l10n_in_transporter_id.name})
        if self.l10n_in_mode in ('2', '3', '4') and self.l10n_in_transporter_doc_date:
            json_payload.update({'transDocDate': self.l10n_in_transporter_doc_date.strftime('%d/%m/%Y')})
        if self.l10n_in_mode == '1' and self.l10n_in_vehicle_type:
            json_payload.update({'vehicleType': self.l10n_in_vehicle_type})
        return json_payload

    def _l10n_in_edi_stock_prepare_stock_json(self):
        self.ensure_one()
        rounding_function = self.env['account.edi.format']._l10n_in_round_value
        extract_digits = self.env['account.edi.format']._l10n_in_edi_extract_digits
        saler_buyer = self._get_l10n_in_edi_stock_saler_buyer_party()
        seller_details = saler_buyer.get('seller_details')
        dispatch_details = saler_buyer.get('dispatch_details')
        buyer_details = saler_buyer.get('buyer_details')
        ship_to_details = saler_buyer.get('ship_to_details')
        line_tax_details = self._get_l10n_in_edi_line_tax_details()
        total_tax_values = self._get_l10n_in_edi_total_tax_values(line_tax_details)
        return {
            "supplyType": self.picking_type_code == 'incoming' and 'I' or 'O',
            "docNo": self.name,
            "docDate": self.date_done.strftime('%d/%m/%Y'),
            "fromGstin": seller_details.commercial_partner_id.vat or 'URP',
            "fromTrdName": seller_details.commercial_partner_id.name,
            "fromStateCode": int(seller_details.state_id.l10n_in_tin),
            "fromAddr1": dispatch_details.street or '',
            "fromAddr2": dispatch_details.street2 or '',
            "fromPlace": dispatch_details.city or '',
            "fromPincode": int(extract_digits(dispatch_details.zip)),
            "actFromStateCode": int(dispatch_details.state_id.l10n_in_tin),
            "toGstin": buyer_details.commercial_partner_id.vat or 'URP',
            "toTrdName": buyer_details.commercial_partner_id.name,
            "toStateCode": int(buyer_details.state_id.l10n_in_tin),
            "toAddr1": ship_to_details.street or '',
            "toAddr2": ship_to_details.street2 or '',
            "toPlace": ship_to_details.city or '',
            "toPincode": int(extract_digits(ship_to_details.zip)),
            "actToStateCode": int(ship_to_details.state_id.l10n_in_tin),
            "itemList": [
                self._get_l10n_in_edi_line_details(line, line_tax_details.get(line, {}), rounding_function)
                for line in self.move_ids_without_package
            ],
            "totalValue": rounding_function(total_tax_values.get("total_excluded", 0.00)),
            "cgstValue": rounding_function(total_tax_values.get("cgst_amount", 0.00)),
            "sgstValue": rounding_function(total_tax_values.get("sgst_amount", 0.00)),
            "igstValue": rounding_function(total_tax_values.get("igst_amount", 0.00)),
            "cessValue": rounding_function(total_tax_values.get("cess_amount", 0.00)),
            "cessNonAdvolValue": rounding_function(total_tax_values.get("cess_non_advol_amount", 0.00)),
            "otherValue": rounding_function(total_tax_values.get("other_amount", 0.00)),
            "totInvValue": rounding_function(total_tax_values.get("total_included", 0.00)),
        }

    def _get_l10n_in_edi_line_details(self, line, line_tax_details, rounding_function):
        line_details = {
            "productName": line.product_id.name,
            "hsnCode": line.product_id.l10n_in_hsn_code,
            "productDesc": line.name,
            "quantity": line.quantity_done,
            "qtyUnit": line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split('-')[0] or 'OTH',
            "taxableAmount": rounding_function(line.l10n_in_price_taxexcl * line.quantity_done),
        }
        if 'igst' in line_tax_details:
            line_details.update({"igstRate": rounding_function(line_tax_details.get("gst_rate"))})
        elif line_tax_details.get("gst_rate"):
            line_details.update({
                "cgstRate": rounding_function(line_tax_details.get("gst_rate") / 2),
                "sgstRate": rounding_function(line_tax_details.get("gst_rate") / 2)
            })
        if line_tax_details.get("cess_rate"):
            line_details.update({"cessRate": rounding_function(line_tax_details.get("cess_rate"))})
        return line_details

    def _get_l10n_in_edi_total_tax_values(self, line_tax_details):
        total_tax_values = {'total_excluded': 0.00, 'cgst_amount': 0.00, 'sgst_amount': 0.00, 'igst_amount': 0.00,
            'cess_amount': 0.00, 'cess_non_advol_amount': 0.00, 'other_amount': 0.00, 'total_included': 0.00}
        for line_tax_detail in line_tax_details.values():
            total_tax_values['total_excluded'] += line_tax_detail.get('total_excluded', 0.00)
            total_tax_values['cgst_amount'] += line_tax_detail.get('cgst_amount', 0.00)
            total_tax_values['sgst_amount'] += line_tax_detail.get('sgst_amount', 0.00)
            total_tax_values['igst_amount'] += line_tax_detail.get('igst_amount', 0.00)
            total_tax_values['cess_amount'] += line_tax_detail.get('cess_amount', 0.00)
            total_tax_values['cess_non_advol_amount'] += line_tax_detail.get('cess_non_advol_amount', 0.00)
            total_tax_values['other_amount'] += line_tax_detail.get('other_amount', 0.00)
            total_tax_values['total_included'] += line_tax_detail.get('total_included', 0.00)
        return total_tax_values

    def _get_l10n_in_edi_stock_saler_buyer_party(self):
        if self.picking_type_code == 'incoming':
            return {
                "seller_details": self.partner_id,
                "dispatch_details": self.partner_id,
                "buyer_details": self.company_id.partner_id,
                "ship_to_details": self.picking_type_id.warehouse_id.partner_id or self.company_id.partner_id,
            }
        return {
            "seller_details": self.company_id.partner_id,
            "dispatch_details": self.picking_type_id.warehouse_id.partner_id or self.company_id.partner_id,
            "buyer_details": self.partner_id,
            "ship_to_details": self.partner_id,
        }

    def _get_l10n_in_edi_line_tax_details(self):
        gst_tag_ids = {
            "igst": self.env.ref("l10n_in.tax_report_line_igst").tag_ids,
            "sgst": self.env.ref("l10n_in.tax_report_line_sgst").tag_ids,
            "cgst": self.env.ref("l10n_in.tax_report_line_cgst").tag_ids,
        }
        all_gst_tag_ids = sum(gst_tag_ids.values(), self.env["account.account.tag"])
        cess_tag_ids = {"cess": self.env.ref("l10n_in.tax_report_line_cess").tag_ids}
        state_cess_tag_ids = {"state_cess": self.env.ref("l10n_in.tax_report_line_state_cess").tag_ids}
        line_tax_details = {}
        for move_line in self.move_ids_without_package:
            line_tax_details.setdefault(move_line, {})
            tax_ids = move_line.l10n_in_tax_ids.flatten_taxes_hierarchy()
            extra_tax_details = {
                "gst_rate": sum(tax.amount for tax in tax_ids if any(
                    tag for tag in tax.invoice_repartition_line_ids.tag_ids if tag in all_gst_tag_ids)),
                "cess_rate": sum(tax.amount for tax in tax_ids if tax.amount_type == "percent" and any(
                    tag for tag in tax.invoice_repartition_line_ids.tag_ids if tag in cess_tag_ids["cess"])),
                "state_cess_rate": sum(tax.amount for tax in tax_ids if tax.amount_type == "percent" and any(
                    tag for tag in tax.invoice_repartition_line_ids.tag_ids if tag in state_cess_tag_ids["state_cess"])
                ),
                "other": 0.00,
            }
            taxes_compute = move_line.l10n_in_tax_ids.compute_all(
                price_unit=move_line.l10n_in_price_taxexcl,
                quantity=move_line.quantity_done,
                product=move_line.product_id,
                handle_price_include=False,
            )
            for tax in taxes_compute["taxes"]:
                is_other_tax = True
                tax_id = self.env["account.tax"].browse(tax["id"])
                tax_repartition_line_id = self.env["account.tax.repartition.line"].browse(
                    tax["tax_repartition_line_id"])
                for tax_key, tag_ids in {**gst_tag_ids, **cess_tag_ids, **state_cess_tag_ids}.items():
                    if tax_id.amount_type != "percent" and "cess" in tax_key:
                        tax_key = tax_key + "_non_advol"
                    if any(tag for tag in tax["tag_ids"] if tag in tag_ids.ids):
                        extra_tax_details.setdefault("%s_amount"%(tax_key), 0.00)
                        extra_tax_details["%s_amount"%(tax_key)] += tax["amount"]
                        is_other_tax = False
                        continue
                if is_other_tax and tax_repartition_line_id.factor_percent > 0.00:
                    extra_tax_details["other"] += tax["amount"]
            line_tax_details[move_line].update({**taxes_compute, **extra_tax_details})
        return line_tax_details

    #================================ API methods ===========================

    @api.model
    def _l10n_in_edi_stock_no_config_response(self):
        return {'error': [{
            'code': '000',
            'message': _(
                "A username and password still needs to be set or it's wrong for the E-WayBill(IN). "
                "It needs to be added and verify in the Settings."
            )}
        ]}

    @api.model
    def _l10n_in_edi_stock_check_authentication(self, company):
        sudo_company = company.sudo()
        if sudo_company.l10n_in_edi_stock_username and sudo_company._l10n_in_edi_stock_token_is_valid():
            return True
        elif sudo_company.l10n_in_edi_stock_username and sudo_company.l10n_in_edi_stock_password:
            authenticate_response = self._l10n_in_edi_stock_authenticate(company)
            if not authenticate_response.get("error"):
                return True
        return False

    @api.model
    def _l10n_in_edi_stock_connect_to_server(self, company, url_path, params):
        user_token = self.env["iap.account"].get("l10n_in_edi")
        params.update({
            "account_token": user_token.account_token,
            "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "username": company.sudo().l10n_in_edi_stock_username,
            "gstin": company.vat,
        })
        if company.sudo().l10n_in_edi_stock_production_env:
            default_endpoint = DEFAULT_IAP_ENDPOINT
        else:
            default_endpoint = DEFAULT_IAP_TEST_ENDPOINT
        endpoint = self.env["ir.config_parameter"].sudo().get_param("l10n_in_edi_stock.endpoint", default_endpoint)
        url = "%s%s" % (endpoint, url_path)
        try:
            return jsonrpc(url, params=params, timeout=25)
        except AccessError as e:
            _logger.warning("Connection error: %s", e.args[0])
            return {
                "error": [{
                    "code": "404",
                    "message": _("Unable to connect to the online E-WayBill service."
                        "The web service may be temporary down. Please try again in a moment.")
                }]
            }

    @api.model
    def _l10n_in_edi_stock_authenticate(self, company):
        params = {"password": company.sudo().l10n_in_edi_stock_password}
        response = self._l10n_in_edi_stock_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/authenticate", params=params
        )
        if response and response.get("status_cd") == '1':
            company.sudo().l10n_in_edi_stock_auth_validity = fields.Datetime.now() + timedelta(
                hours=6, minutes=00, seconds=00)
            self.env.cr.commit()
        return response

    @api.model
    def _l10n_in_edi_stock_submit(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_stock_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_stock_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_stock_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/generate", params=params
        )

    @api.model
    def _l10n_in_edi_stock_cancel(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_stock_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_stock_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_stock_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/cancel", params=params
        )

    @api.model
    def _l10n_in_edi_stock_update_part_b(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_stock_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_stock_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_stock_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/vehewb", params=params
        )

    @api.model
    def _l10n_in_edi_stock_update_transporter(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_stock_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_stock_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_stock_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/updatetransporter", params=params
        )

    @api.model
    def _l10n_in_edi_stock_extend(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_stock_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_stock_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_stock_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/extendvalidity", params=params
        )

    @api.model
    def _get_l10n_in_edi_stock_details_by_consigner(self, company, document_type, document_number):
        is_authenticated = self._l10n_in_edi_stock_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_stock_no_config_response()
        params = {"document_type": document_type, "document_number": document_number}
        return self._l10n_in_edi_stock_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/getewaybillgeneratedbyconsigner", params=params
        )
