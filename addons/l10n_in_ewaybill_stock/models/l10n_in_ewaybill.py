# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re
import markupsafe
import logging

from odoo import fields, models, api, _
from odoo.fields import Command
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools import html_escape, html2plaintext

from odoo.addons.iap import jsonrpc
from odoo.addons.l10n_in_edi.models.account_edi_format import DEFAULT_IAP_ENDPOINT, DEFAULT_IAP_TEST_ENDPOINT
from odoo.addons.l10n_in_edi_ewaybill.models.error_codes import ERROR_CODES

from datetime import timedelta
from markupsafe import Markup


_logger = logging.getLogger(__name__)


class EwaybillStock(models.Model):
    _name = "l10n.in.ewaybill"
    _description = "Ewaybill for stock movement"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    stock_picking_id = fields.Many2one("stock.picking", "Stock Transfer", required=True, readonly=True)
    date = fields.Datetime("Date", compute="_compute_date", store=True)

    ewaybill_line_ids = fields.One2many("l10n.in.ewaybill.line", "ewaybill_id", compute="_compute_ewaybill_line_ids", store=True, readonly=False)

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        compute='_compute_partner_id', store=True)

    attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        groups='base.group_system',
        help="The file generated when the ewaybill is posted (and this document is processed).")

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        compute='_compute_company_id', store=True,
        index=True)

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        tracking=True,
        compute='_compute_currency_id', store=True)

    amount_untaxed = fields.Monetary(string="Untaxed Amount", store=True, compute='_compute_amounts', tracking=5)
    amount_total = fields.Monetary(string="Total", store=True, compute='_compute_amounts', tracking=4)
    tax_totals = fields.Binary(compute='_compute_tax_totals')
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default='pending')

    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        compute='_compute_partner_shipping_id', store=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="The delivery address will be used in the computation of the fiscal position.")

    gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
            ('uin_holders', 'UIN Holders'),
        ], string="GST Treatment", compute="_compute_gst_treatment", store=True, readonly=False, copy=True)

    type_id = fields.Many2one("l10n.in.ewaybill.type", "E-waybill Document Type", tracking=True)

    transporter_id = fields.Many2one("res.partner", "Transporter", copy=False, tracking=True)
    distance = fields.Integer("Distance", tracking=True)
    mode = fields.Selection([
        ("1", "Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship")],
        string="Transportation Mode", copy=False, tracking=True)

    # Vehicle Number and Type required when transportation mode is By Road.
    vehicle_no = fields.Char("Vehicle Number", copy=False, tracking=True)
    vehicle_type = fields.Selection([
        ("R", "Regular"),
        ("O", "ODC")],
        string="Vehicle Type", copy=False, tracking=True)

    transportation_doc_no = fields.Char(
        string="Transportation Document Number",
        help="""Transport document number. If it is more than 15 chars, last 15 chars may be entered""",
        copy=False, tracking=True)

    transportation_doc_date = fields.Date(
        string="Document Date",
        help="Date on the transporter document",
        copy=False, tracking=True)

    state_id = fields.Many2one('res.country.state', string="Place of supply", compute="_compute_state_id", store=True, readonly=False)

    ewaybill_number = fields.Char("Ewaybill Number", compute="_compute_ewaybill_number", store=True)
    cancel_reason = fields.Selection(selection=[
        ("1", "Duplicate"),
        ("2", "Data Entry Mistake"),
        ("3", "Order Cancelled"),
        ("4", "Others"),
        ], string="Cancel reason", copy=False, tracking=True)
    cancel_remarks = fields.Char("Cancel remarks", copy=False, tracking=True)

    @api.depends('attachment_id')
    def _compute_ewaybill_number(self):
        for ewaybill in self:
            ewaybill_response_json = ewaybill._get_l10n_in_edi_ewaybill_response_json()
            if ewaybill_response_json:
                ewaybill.ewaybill_number = ewaybill_response_json.get("ewayBillNo") or ewaybill_response_json.get("EwbNo")
            else:
                ewaybill.ewaybill_number = False

    @api.depends('stock_picking_id')
    def _compute_date(self):
        for record in self:
            record.date = record.stock_picking_id.scheduled_date

    @api.depends('stock_picking_id')
    def _compute_ewaybill_line_ids(self):
        for record in self:
            if not record.stock_picking_id:
                record.ewaybill_line_ids = False
            else:
                lines = self.env['stock.move'].search([('picking_id', '=', record.stock_picking_id.id)])
                record.ewaybill_line_ids = [Command.delete(line.id) for line in record.ewaybill_line_ids]
                record.ewaybill_line_ids = lines.mapped(lambda line: Command.create({
                    'stock_move_id': line.id,
                }))

    @api.depends('stock_picking_id.company_id')
    def _compute_company_id(self):
        for record in self:
            record.company_id = record.stock_picking_id.company_id

    @api.depends('company_id')
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.company_id.currency_id

    @api.depends('stock_picking_id.partner_id')
    def _compute_partner_id(self):
        for record in self:
            record.partner_id = record.stock_picking_id.partner_id

    @api.depends('partner_id', 'company_id')
    def _compute_state_id(self):
        for ewaybill in self:
            ewaybill.state_id = ewaybill.partner_id.state_id

    @api.depends('partner_id')
    def _compute_partner_shipping_id(self):
        for ewaybill in self:
            addr = ewaybill.partner_id.address_get(['delivery'])
            ewaybill.partner_shipping_id = addr and addr.get('delivery')

    @api.depends('partner_id')
    def _compute_gst_treatment(self):
        for record in self:
            gst_treatment = record.partner_id.l10n_in_gst_treatment
            if not gst_treatment:
                gst_treatment = 'unregistered'
                if record.partner_id.country_id.code == 'IN' and record.partner_id.vat:
                    gst_treatment = 'regular'
                elif record.partner_id.country_id and record.partner_id.country_id.code != 'IN':
                    gst_treatment = 'overseas'
            record.gst_treatment = gst_treatment

    @api.depends('ewaybill_line_ids')
    def _compute_amounts(self):
        for record in self:
            amount_untaxed = 0.0
            amount_tax = 0.0

            for rec in record.ewaybill_line_ids:
                amount_untaxed += rec.price_subtotal
                amount_tax += rec.cgst_amount + rec.sgst_amount + rec.igst_amount + rec.cess_amount + rec.cess_non_advol_amount + rec.other_amount

            record.amount_untaxed = amount_untaxed
            record.amount_total = amount_untaxed + amount_tax

    @api.depends('ewaybill_line_ids.tax_ids', 'ewaybill_line_ids.price_unit', 'amount_total', 'amount_untaxed', 'currency_id')
    def _compute_tax_totals(self):
        for record in self:
            lines = record.ewaybill_line_ids
            record.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in lines],
                record.currency_id or record.company_id.currency_id,
            )

    def ewaybill_cancel(self):
        for ewaybill in self:
            if ewaybill.state == "sent" and (not ewaybill.cancel_reason or not ewaybill.cancel_remarks):
                raise UserError(_("To cancel E-waybill set cancel reason and remarks\n"))
            res = ewaybill._l10n_in_ewaybill_cancel_invoice(ewaybill)
            if res.get('success') is True:
                ewaybill.message_post(body=_("A cancellation of the Ewaybill has been requested."))
                ewaybill.write({'state': 'cancel'})
            else:
                raise ValidationError(_("\nEwaybill not cancelled \n\n%s") % (html2plaintext(res.get(ewaybill).get("error", False))))

    def ewaybill_send(self):
        for ewaybill in self:
            errors = self._check_ewaybill_configuration(ewaybill)
            if errors:
                raise UserError(_("Invalid invoice configuration:\n%s") % '\n'.join(errors))

            res = ewaybill._l10n_in_ewaybill_post_invoice_edi(ewaybill)
            if res.get(ewaybill).get("success") is True:
                ewaybill.write({
                    'state': 'sent',
                    'attachment_id' : res.get(ewaybill).get('attachment'),
                })
                stock_picking = self.env['stock.picking'].browse(ewaybill.stock_picking_id.id)
                stock_picking.write({'ewaybill_id': self.id})
            else:
                raise ValidationError(_("\nEwaybill not sent\n\n%s") % (html2plaintext(res.get(ewaybill).get("error", False))))

    def ewaybill_update_part_b(self):
        return {
            'name': _('Update Part-B'),
            'res_model': 'ewaybill.update.part.b',
            'view_mode': 'form',
            'context': {
                'default_ewaybill_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def ewaybill_update_transporter(self):
        return {
            'name': _('Update Transporter'),
            'res_model': 'ewaybill.update.transporter',
            'view_mode': 'form',
            'context': {
                'default_ewaybill_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def ewaybill_extend_validity(self):
        return {
            'name': _('Extend Validity'),
            'res_model': 'ewaybill.extend.validity',
            'view_mode': 'form',
            'context': {
                'default_ewaybill_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _check_ewaybill_configuration(self, ewaybill):
        error_message = []
        if not ewaybill.type_id:
            error_message.append(_("- Document Type"))
        if not ewaybill.mode:
            error_message.append(_("- Transportation Mode"))
        elif ewaybill.mode == "1":
            if not ewaybill.vehicle_no and ewaybill.vehicle_type:
                error_message.append(_("- Vehicle Number and Type is required when Transportation Mode is By Road"))
        elif ewaybill.mode in ("2", "3", "4"):
            if not ewaybill.transportation_doc_no and ewaybill.transportation_doc_date:
                error_message.append(_("- Transport document number and date is required when Transportation Mode is Rail,Air or Ship"))
        if error_message:
            error_message.insert(0, _("The following information are missing on the invoice (see eWayBill tab):"))
        error_message += self._l10n_in_validate_partner(ewaybill.partner_id)
        error_message += self._l10n_in_validate_partner(ewaybill.company_id.partner_id, is_company=True)
        goods_line_is_available = False
        for line in ewaybill.ewaybill_line_ids.filtered(lambda line: line.product_id.type != "service"):
            goods_line_is_available = True
            if line.product_id:
                hsn_code = self._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code)
                if not hsn_code:
                    error_message.append(_("HSN code is not set in product %s", line.product_id.name))
                elif not re.match("^[0-9]+$", hsn_code):
                    error_message.append(_(
                        "Invalid HSN Code (%s) in product %s", hsn_code, line.product_id.name
                    ))
            else:
                error_message.append(_("product is required to get HSN code"))
        if not goods_line_is_available:
            error_message.append(_('You need at least one product having "Product Type" as stockable or consumable.'))
        if error_message:
            error_message.insert(0, _("Impossible to send the Ewaybill."))
        return error_message

    def _l10n_in_validate_partner(self, partner, is_company=False):
        self.ensure_one()
        message = []
        if not re.match("^.{3,100}$", partner.street or ""):
            message.append(_("\n- Street required min 3 and max 100 characters"))
        if partner.street2 and not re.match("^.{3,100}$", partner.street2):
            message.append(_("\n- Street2 should be min 3 and max 100 characters"))
        if not re.match("^.{3,100}$", partner.city or ""):
            message.append(_("\n- City required min 3 and max 100 characters"))
        if not re.match("^.{3,50}$", partner.state_id.name or ""):
            message.append(_("\n- State required min 3 and max 50 characters"))
        if partner.country_id.code == "IN" and not re.match("^[0-9]{6,}$", partner.zip or ""):
            message.append(_("\n- Zip code required 6 digits"))
        if partner.phone and not re.match("^[0-9]{10,12}$",
            self._l10n_in_edi_extract_digits(partner.phone)
        ):
            message.append(_("\n- Mobile number should be minimum 10 or maximum 12 digits"))
        if partner.email and (
            not re.match(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$", partner.email)
            or not re.match("^.{6,100}$", partner.email)
        ):
            message.append(_("\n- Email address should be valid and not more then 100 characters"))
        return message

    def _l10n_in_ewaybill_post_invoice_edi(self, ewaybill):
        response = {}
        res = {}
        generate_json = self._l10n_in_ewaybill_generate_json(ewaybill)
        response = self._l10n_in_edi_ewaybill_generate(ewaybill.company_id, generate_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_ewaybill_authenticate(ewaybill.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_ewaybill_generate(ewaybill.company_id, generate_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "604" in error_codes:
                # Get E-waybill by details in case of E-waybill is already generated
                # this happens when timeout from the Government portal but E-waybill is generated
                response = self._l10n_in_edi_ewaybill_get_by_consigner(
                    ewaybill.company_id, generate_json.get("docType"), generate_json.get("docNo"))
                if not response.get("error"):
                    error = []
                    odoobot = self.env.ref("base.partner_root")
                    ewaybill.message_post(author_id=odoobot.id, body=
                        _("Somehow this E-waybill has been generated in the government portal before. You can verify by checking the invoice details into the government (https://ewaybillgst.gov.in/Others/EBPrintnew.asp)")
                    )
            if "no-credit" in error_codes:
                res[ewaybill] = {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(ewaybill.company_id),
                    "blocking_level": "error",
                }
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message") or self._l10n_in_ewaybill_get_error_message(e.get('code')))) for e in error])
                blocking_level = "error"
                if "404" in error_codes:
                    blocking_level = "warning"
                res[ewaybill] = {
                    "success": False,
                    "error": error_message,
                    "blocking_level": blocking_level,
                }
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_ewaybill.json" % (ewaybill.stock_picking_id.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "l10n.in.ewaybill",
                "res_id": ewaybill.id,
                "mimetype": "application/json",
            })
            inv_res = {"success": True, "attachment": attachment}
            res[ewaybill] = inv_res
        return res

    def _l10n_in_ewaybill_cancel_invoice(self, ewaybill):
        response = {}
        res = {}
        ewaybill_response_json = ewaybill._get_l10n_in_edi_ewaybill_response_json()
        cancel_json = {
            "ewbNo": ewaybill_response_json.get("ewayBillNo") or ewaybill_response_json.get("EwbNo"),
            "cancelRsnCode": int(ewaybill.cancel_reason),
            "CnlRem": ewaybill.cancel_remarks,
        }
        response = self._l10n_in_edi_ewaybill_cancel(ewaybill.company_id, cancel_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_ewaybill_authenticate(ewaybill.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_ewaybill_cancel(ewaybill.company_id, cancel_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "312" in error_codes:
                # E-waybill is already canceled
                # this happens when timeout from the Government portal but IRN is generated
                error_message = Markup("<br/>").join([Markup("[%s] %s") % (e.get("code"), e.get("message") or self._l10n_in_edi_ewaybill_get_error_message(e.get('code'))) for e in error])
                error = []
                response = {"data": ""}
                odoobot = self.env.ref("base.partner_root")
                ewaybill.message_post(author_id=odoobot.id, body=
                    Markup("%s<br/>%s:<br/>%s") % (
                        _("Somehow this E-waybill has been canceled in the government portal before. You can verify by checking the details into the government (https://ewaybillgst.gov.in/Others/EBPrintnew.asp)"),
                        _("Error"),
                        error_message
                    )
                )
            if "no-credit" in error_codes:
                res[ewaybill] = {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(ewaybill.company_id),
                    "blocking_level": "error",
                }
            elif error:
                error_message = Markup("<br/>").join([Markup("[%s] %s") % (e.get("code"), e.get("message") or self._l10n_in_edi_ewaybill_get_error_message(e.get('code'))) for e in error])
                blocking_level = "error"
                if "404" in error_codes:
                    blocking_level = "warning"
                res[ewaybill] = {
                    "success": False,
                    "error": error_message,
                    "blocking_level": blocking_level,
                }
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_ewaybill_cancel.json" % (ewaybill.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "l10n.in.ewaybill",
                "res_id": ewaybill.id,
                "mimetype": "application/json",
            })
            inv_res = {"success": True, "attachment": attachment}
            res[ewaybill] = inv_res
        return res

    def _l10n_in_edi_get_iap_buy_credits_message(self, company):
        base_url = "https://iap-sandbox.odoo.com/iap/1/credit" if not company.sudo().l10n_in_edi_production_env else ""
        url = self.env["iap.account"].get_credits_url(service_name="l10n_in_edi", base_url=base_url)
        return markupsafe.Markup("""<p><b>%s</b></p><p>%s <a href="%s">%s</a></p>""") % (
            _("You have insufficient credits to send this document!"),
            _("Please buy more credits and retry: "),
            url,
            _("Buy Credits")
        )

    def _l10n_in_ewaybill_update_part_b(self, ewaybill, val):
        response = {}
        res = {}
        ewaybill_response_json = ewaybill._get_l10n_in_edi_ewaybill_response_json()

        update_part_b_json = {
            "ewbNo": ewaybill_response_json.get("ewayBillNo") or ewaybill_response_json.get("EwbNo"),
            "vehicleNo": val.get("vehicle_no") or "",
            "fromPlace": val.get("update_place") or "",
            "fromStateCode": int(val.get("update_state_id").l10n_in_tin) or "",
            "reasonCode" : int(val.get("update_reason_code")),
            "reasonRem" : val.get("update_remarks"),
            "transDocNo": val.get("transportation_doc_no") or "",
            "transDocDate": val.get("transportation_doc_date") and
                    val.get("transportation_doc_date").strftime("%d/%m/%Y") or "",
            "transMode": val.get("mode"),
            "vehicleType": val.get("vehicle_type") or "",
        }
        response = self._l10n_in_edi_ewaybill_update_part_b(ewaybill.company_id, update_part_b_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_ewaybill_authenticate(ewaybill.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_ewaybill_generate(ewaybill.company_id, update_part_b_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "no-credit" in error_codes:
                res[ewaybill] = {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(ewaybill.company_id),
                    "blocking_level": "error",
                }
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message") or self._l10n_in_edi_ewaybill_get_error_message(e.get('code')))) for e in error])
                blocking_level = "error"
                if "404" in error_codes:
                    blocking_level = "warning"
                res[ewaybill] = {
                    "success": False,
                    "error": error_message,
                    "blocking_level": blocking_level,
                }
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_ewaybill_updatepartb.json" % (ewaybill.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "l10n.in.ewaybill",
                "res_id": ewaybill.id,
                "mimetype": "application/json",
            })
            inv_res = {"success": True, "attachment": attachment}
            res[ewaybill] = inv_res
        return res

    def _l10n_in_ewaybill_update_transporter(self, ewaybill, val):
        response = {}
        res = {}
        ewaybill_response_json = ewaybill._get_l10n_in_edi_ewaybill_response_json()
        update_transporter_json = {
            "ewbNo": ewaybill_response_json.get("ewayBillNo") or ewaybill_response_json.get("EwbNo"),
            "transporterId": val.get("transporter_id"),
        }
        response = self._l10n_in_edi_ewaybill_update_transporter(ewaybill.company_id, update_transporter_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_ewaybill_authenticate(ewaybill.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_ewaybill_generate(ewaybill.company_id, update_transporter_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "no-credit" in error_codes:
                res[ewaybill] = {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(ewaybill.company_id),
                    "blocking_level": "error",
                }
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message") or self._l10n_in_edi_ewaybill_get_error_message(e.get('code')))) for e in error])
                blocking_level = "error"
                if "404" in error_codes:
                    blocking_level = "warning"
                res[ewaybill] = {
                    "success": False,
                    "error": error_message,
                    "blocking_level": blocking_level,
                }
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_ewaybill_update_transporter.json" % (ewaybill.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "l10n.in.ewaybill",
                "res_id": ewaybill.id,
                "mimetype": "application/json",
            })
            inv_res = {"success": True, "attachment": attachment}
            res[ewaybill] = inv_res
        return res

    def _l10n_in_ewaybill_extend_validity(self, ewaybill, val):
        response = {}
        res = {}
        ewaybill_response_json = ewaybill._get_l10n_in_edi_ewaybill_response_json()
        extend_validity_json = {
            "ewbNo": ewaybill_response_json.get("ewayBillNo") or ewaybill_response_json.get("EwbNo"),
            "vehicleNo": val.get("vehicle_no") or "",
            "fromPlace": val.get("current_place"),
            "fromStateCode": int(val.get("current_state_id").l10n_in_tin) or "",
            "remainingDistance": val.get("rem_distance"),
            "transDocNo": val.get("transportation_doc_no") or "",
            "transDocDate": val.get("transportation_doc_date") and
                    val.get("transportation_doc_date").strftime("%d/%m/%Y") or "",
            "transMode": val.get("mode"),
            "extnRsnCode": val.get("extend_reason_code"),
            "extnRemarks": val.get("extend_reason_remarks"),
            "fromPincode": int(self._l10n_in_edi_extract_digits(val.get("current_pincode"))),
            "consignmentStatus": val.get("mode") in ('1', '2', '3', '4') and "M" or "T",
            "transitType": val.get("consignment_status") == "T" and val.get("transit_type") or "",
        }
        response = self._l10n_in_edi_ewaybill_extend_validity(ewaybill.company_id, extend_validity_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_ewaybill_authenticate(ewaybill.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_ewaybill_generate(ewaybill.company_id, extend_validity_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "no-credit" in error_codes:
                res[ewaybill] = {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(ewaybill.company_id),
                    "blocking_level": "error",
                }
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message") or self._l10n_in_edi_ewaybill_get_error_message(e.get('code')))) for e in error])
                blocking_level = "error"
                if "404" in error_codes:
                    blocking_level = "warning"
                res[ewaybill] = {
                    "success": False,
                    "error": error_message,
                    "blocking_level": blocking_level,
                }
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_ewaybill_extendvalidity.json" % (ewaybill.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "l10n.in.ewaybill",
                "res_id": ewaybill.id,
                "mimetype": "application/json",
            })
            inv_res = {"success": True, "attachment": attachment}
            res[ewaybill] = inv_res
        return res

    def _get_l10n_in_edi_ewaybill_response_json(self):
        self.ensure_one()
        for ewaybill in self:
            if ewaybill.state == "sent" and ewaybill.attachment_id:
                return json.loads(ewaybill.sudo().attachment_id.raw.decode("utf-8"))
            else:
                return {}

    def _get_l10n_in_edi_saler_buyer_party(self, ewaybill):
        return {
            "seller_details": ewaybill.company_id.partner_id,
            "dispatch_details": ewaybill.stock_picking_id.picking_type_id.warehouse_id.partner_id or ewaybill.company_id.partner_id,
            "buyer_details": ewaybill.partner_id,
            "ship_to_details": ewaybill.partner_shipping_id or ewaybill.partner_id,
        }

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

    def _l10n_in_ewaybill_generate_json(self, ewaybill):
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

        saler_buyer = self._get_l10n_in_edi_saler_buyer_party(ewaybill)
        seller_details = saler_buyer.get("seller_details")
        dispatch_details = saler_buyer.get("dispatch_details")
        buyer_details = saler_buyer.get("buyer_details")
        ship_to_details = saler_buyer.get("ship_to_details")
        sign = ewaybill.stock_picking_id.picking_type_id.code == "outgoing" and -1 or 1
        extract_digits = self._l10n_in_edi_extract_digits
        json_payload = {
            "supplyType": ewaybill.stock_picking_id.picking_type_id.code == "outgoing" and "O" or "I",
            "subSupplyType": ewaybill.type_id.sub_type_code,
            "docType": ewaybill.type_id.code,
            "transactionType": get_transaction_type(seller_details, dispatch_details, buyer_details, ship_to_details),
            "transDistance": str(ewaybill.distance),
            "docNo": ewaybill.stock_picking_id.name,
            "docDate": ewaybill.date.strftime("%d/%m/%Y"),
            "fromGstin": seller_details.country_id.code == "IN" and seller_details.commercial_partner_id.vat or "URP",
            "fromTrdName": seller_details.commercial_partner_id.name,
            "fromAddr1": dispatch_details.street or "",
            "fromAddr2": dispatch_details.street2 or "",
            "fromPlace": dispatch_details.city or "",
            "fromPincode": dispatch_details.country_id.code == "IN" and int(extract_digits(dispatch_details.zip)) or "",
            "fromStateCode": int(seller_details.state_id.l10n_in_tin) or "",
            "actFromStateCode": dispatch_details.state_id.l10n_in_tin and int(dispatch_details.state_id.l10n_in_tin) or "",
            "toGstin": buyer_details.country_id.code == "IN" and buyer_details.commercial_partner_id.vat or "URP",
            "toTrdName": buyer_details.commercial_partner_id.name,
            "toAddr1": ship_to_details.street or "",
            "toAddr2": ship_to_details.street2 or "",
            "toPlace": ship_to_details.city or "",
            "toPincode": int(extract_digits(ship_to_details.zip)),
            "actToStateCode": int(ship_to_details.state_id.l10n_in_tin),
            "toStateCode": int(buyer_details.state_id.l10n_in_tin),
            "itemList": [
                self._get_l10n_in_ewaybill_line_details(line, sign)
                for line in ewaybill.ewaybill_line_ids
            ],
            "totalValue": self._l10n_in_round_value(ewaybill.amount_untaxed),
            "cgstValue": self._l10n_in_round_value(sum(ewaybill.ewaybill_line_ids.mapped('cgst_amount'))),
            "sgstValue": self._l10n_in_round_value(sum(ewaybill.ewaybill_line_ids.mapped('sgst_amount'))),
            "igstValue": self._l10n_in_round_value(sum(ewaybill.ewaybill_line_ids.mapped('igst_amount'))),
            "cessValue": self._l10n_in_round_value(sum(ewaybill.ewaybill_line_ids.mapped('cess_amount'))),
            "cessNonAdvolValue": self._l10n_in_round_value(sum(ewaybill.ewaybill_line_ids.mapped('cess_non_advol_amount'))),
            "otherValue": self._l10n_in_round_value(sum(ewaybill.ewaybill_line_ids.mapped('other_amount'))),
            "totInvValue": self._l10n_in_round_value(ewaybill.amount_total),
        }
        if ewaybill.transporter_id:
            json_payload.update({
            "transporterId": ewaybill.transporter_id.vat,
            "transporterName": ewaybill.transporter_id.name,
            })
        is_overseas = ewaybill.gst_treatment in ("overseas", "special_economic_zone")
        if is_overseas:
            json_payload.update({"toStateCode": 99})
        if is_overseas and ship_to_details.state_id.country_id.code != "IN":
            json_payload.update({
                "actToStateCode": 99,
                "toPincode": 999999,
            })
        else:
            json_payload.update({
                "actToStateCode": int(ship_to_details.state_id.l10n_in_tin),
                "toPincode": int(extract_digits(ship_to_details.zip)),
            })

        if ewaybill.mode in ("2", "3", "4"):
            json_payload.update({
                "transMode": ewaybill.mode,
                "transDocNo": ewaybill.transportation_doc_no or "",
                "transDocDate": ewaybill.transportation_doc_date and
                    ewaybill.transportation_doc_date.strftime("%d/%m/%Y") or "",
            })
        if ewaybill.mode == "1":
            json_payload.update({
                "transMode": ewaybill.mode,
                "vehicleNo": ewaybill.vehicle_no or "",
                "vehicleType": ewaybill.vehicle_type or "",
            })
        return json_payload

    def _get_l10n_in_ewaybill_line_details(self, line, sign):
        extract_digits = self._l10n_in_edi_extract_digits
        line_details = {
            "productName": line.product_id.name,
            "hsnCode": extract_digits(line.product_id.l10n_in_hsn_code),
            "productDesc": line.product_id.name,
            "quantity": line.quantity,
            "qtyUnit": line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split("-")[0] or "OTH",
            "taxableAmount": self._l10n_in_round_value(line.price_unit * sign),
        }
        if line.igst_rate:
            line_details.update({"igstRate": self._l10n_in_round_value(line.igst_rate)})
        else:
            line_details.update({
                "cgstRate": self._l10n_in_round_value(line.cgst_rate),
                "sgstRate": self._l10n_in_round_value(line.sgst_rate),
            })
        if line.cess_rate:
            line_details.update({"cessRate": self._l10n_in_round_value(line.cess_rate)})
        return line_details

    def _l10n_in_ewaybill_get_error_message(self, code):
        error_message = ERROR_CODES.get(code)
        return error_message or _("We don't know the error message for this error code. Please contact support.")

    #=============================== E-waybill API methods ===================================

    @api.model
    def _l10n_in_edi_ewaybill_no_config_response(self):
        return {"error": [{
            "code": "0",
            "message": _(
                "Unable to send E-waybill."
                "Create an API user in NIC portal, and set it using the top menu: Configuration > Settings."
            )}
        ]}

    @api.model
    def _l10n_in_edi_ewaybill_check_authentication(self, company):
        sudo_company = company.sudo()
        if sudo_company.l10n_in_edi_ewaybill_username and sudo_company._l10n_in_edi_ewaybill_token_is_valid():
            return True
        elif sudo_company.l10n_in_edi_ewaybill_username and sudo_company.l10n_in_edi_ewaybill_password:
            authenticate_response = self._l10n_in_edi_ewaybill_authenticate(company)
            if not authenticate_response.get("error"):
                return True
        return False

    @api.model
    def _l10n_in_edi_ewaybill_connect_to_server(self, company, url_path, params):
        user_token = self.env["iap.account"].get("l10n_in_edi")
        params.update({
            "account_token": user_token.account_token,
            "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "username": company.sudo().l10n_in_edi_ewaybill_username,
            "gstin": company.vat,
        })
        if company.sudo().l10n_in_edi_production_env:
            default_endpoint = DEFAULT_IAP_ENDPOINT
        else:
            default_endpoint = DEFAULT_IAP_TEST_ENDPOINT
        endpoint = self.env["ir.config_parameter"].sudo().get_param("l10n_in_edi_ewaybill.endpoint", default_endpoint)
        url = "%s%s" % (endpoint, url_path)
        try:
            return jsonrpc(url, params=params, timeout=70)
        except AccessError as e:
            _logger.warning("Connection error: %s", e.args[0])
            return {
                "error": [{
                    "code": "access_error",
                    "message": _("Unable to connect to the E-WayBill service."
                        "The web service may be temporary down. Please try again in a moment.")
                }]
            }

    @api.model
    def _l10n_in_edi_ewaybill_authenticate(self, company):
        params = {"password": company.sudo().l10n_in_edi_ewaybill_password}
        response = self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/authenticate", params=params
        )
        if response and response.get("status_cd") == "1":
            company.sudo().l10n_in_edi_ewaybill_auth_validity = fields.Datetime.now() + timedelta(
                hours=6, minutes=00, seconds=00)
        return response

    @api.model
    def _l10n_in_edi_ewaybill_generate(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/generate", params=params
        )

    @api.model
    def _l10n_in_edi_ewaybill_cancel(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/cancel", params=params
        )

    @api.model
    def _l10n_in_edi_ewaybill_get_by_consigner(self, company, document_type, document_number):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"document_type": document_type, "document_number": document_number}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/getewaybillgeneratedbyconsigner", params=params
        )

    @api.model
    def _l10n_in_edi_ewaybill_update_part_b(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/updatepartb", params=params
        )

    @api.model
    def _l10n_in_edi_ewaybill_update_transporter(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/updatetransporter", params=params
        )

    @api.model
    def _l10n_in_edi_ewaybill_extend_validity(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/extendvalidity", params=params
        )
