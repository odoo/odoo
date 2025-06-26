# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import pytz
import re
from collections import defaultdict
from datetime import datetime

import psycopg2.errors

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.l10n_in_ewaybill_stock.tools.ewaybill_api import EWayBillApi, EWayBillError


_logger = logging.getLogger(__name__)


class Ewaybill(models.Model):
    _name = "l10n.in.ewaybill"
    _description = "e-Waybill"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    # Ewaybill details generated from the API
    name = fields.Char("e-Waybill Number", copy=False, readonly=True, tracking=True)
    ewaybill_date = fields.Date("e-Waybill Date", copy=False, readonly=True, tracking=True)
    ewaybill_expiry_date = fields.Date("e-Waybill Valid Upto", copy=False, readonly=True, tracking=True)

    state = fields.Selection(string='Status', selection=[
        ('pending', 'Pending'),
        ('challan', 'Challan'),
        ('generated', 'Generated'),
        ('cancel', 'Cancelled'),
    ], required=True, readonly=True, copy=False, tracking=True, default='pending')

    # Stock picking details
    picking_id = fields.Many2one("stock.picking", "Stock Transfer", copy=False)
    move_ids = fields.One2many(related="picking_id.move_ids")
    picking_type_code = fields.Selection(related='picking_id.picking_type_id.code')

    # Document details
    document_date = fields.Datetime("Document Date", related="picking_id.date_done")
    document_number = fields.Char("Document", related="picking_id.name")
    company_id = fields.Many2one("res.company", related="picking_id.company_id")
    company_currency_id = fields.Many2one(related="company_id.currency_id")
    supply_type = fields.Selection(string="Supply Type", selection=[
        ("O", "Outward"),
        ("I", "Inward")
    ], compute="_compute_supply_type")
    partner_bill_from_id = fields.Many2one(
        "res.partner",
        string='Bill From',
        compute="_compute_document_partners_details",
        check_company=True,
        store=True,
        readonly=False
    )
    partner_bill_to_id = fields.Many2one(
        "res.partner",
        string='Bill To',
        compute="_compute_document_partners_details",
        check_company=True,
        store=True,
        readonly=False
    )
    partner_ship_from_id = fields.Many2one(
        "res.partner",
        string='Dispatch From',
        compute="_compute_document_partners_details",
        check_company=True,
        store=True,
        readonly=False
    )
    partner_ship_to_id = fields.Many2one(
        'res.partner',
        string='Ship To',
        compute='_compute_document_partners_details',
        check_company=True,
        store=True,
        readonly=False
    )

    # Fields to determine which partner details are editable
    is_bill_to_editable = fields.Boolean(compute="_compute_is_editable")
    is_bill_from_editable = fields.Boolean(compute="_compute_is_editable")
    is_ship_to_editable = fields.Boolean(compute="_compute_is_editable")
    is_ship_from_editable = fields.Boolean(compute="_compute_is_editable")

    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        string="Fiscal Position",
        compute="_compute_fiscal_position",
        check_company=True,
        store=True,
        readonly=False
    )

    # E-waybill Document Type
    type_id = fields.Many2one("l10n.in.ewaybill.type", "Document Type", tracking=True, required=True)
    sub_type_code = fields.Char(related="type_id.sub_type_code")
    type_description = fields.Char(string="Description")

    # Transportation details
    distance = fields.Integer("Distance", tracking=True)
    mode = fields.Selection([
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship or Ship Cum Road/Rail")
    ], string="Transportation Mode", copy=False, tracking=True, default="1")

    # Vehicle Number and Type required when transportation mode is By Road.
    vehicle_no = fields.Char("Vehicle Number", copy=False, tracking=True)
    vehicle_type = fields.Selection([
        ("R", "Regular"),
        ("O", "Over Dimensional Cargo")],
        string="Vehicle Type",
        compute="_compute_vehicle_type",
        store=True,
        copy=False,
        tracking=True,
        readonly=False
    )

    # Document number and date required in case of transportation mode is Rail, Air or Ship.
    transportation_doc_no = fields.Char(
        string="Transporter Doc No",
        copy=False, tracking=True)
    transportation_doc_date = fields.Date(
        string="Transporter Doc Date",
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
            ewaybill.supply_type = ewaybill.picking_type_code == 'incoming' and 'I' or 'O'

    @api.depends('picking_id')
    def _compute_document_partners_details(self):
        for ewaybill in self.filtered(lambda ewb: ewb.state == 'pending'):
            picking_id = ewaybill.picking_id
            if ewaybill.picking_type_code == 'incoming':
                ewaybill.partner_bill_to_id = picking_id.company_id.partner_id
                ewaybill.partner_bill_from_id = picking_id.partner_id
                ewaybill.partner_ship_to_id = picking_id.picking_type_id.warehouse_id.partner_id
                ewaybill.partner_ship_from_id = picking_id.partner_id
            else:
                ewaybill.partner_bill_to_id = picking_id.partner_id
                ewaybill.partner_bill_from_id = picking_id.company_id.partner_id
                ewaybill.partner_ship_to_id = picking_id.partner_id
                ewaybill.partner_ship_from_id = picking_id.picking_type_id.warehouse_id.partner_id
                if partner_invoice_id := ewaybill.picking_id._l10n_in_get_invoice_partner():
                    ewaybill.partner_bill_to_id = partner_invoice_id

            if (
                ewaybill.picking_type_code == 'dropship' and
                (dest_partner := ewaybill.picking_id._get_l10n_in_dropship_dest_partner())
            ):
                ewaybill.partner_ship_to_id = dest_partner
                ewaybill.partner_ship_from_id = ewaybill.picking_id.partner_id

    @api.depends('partner_bill_from_id', 'partner_bill_to_id')
    def _compute_fiscal_position(self):
        for ewaybill in self.filtered(lambda ewb: ewb.state == 'pending'):
            ewaybill.fiscal_position_id = (
                self.env['account.fiscal.position'].with_company(ewaybill.company_id)._get_fiscal_position(
                    ewaybill.picking_type_code == 'incoming'
                    and ewaybill.partner_bill_from_id
                    or ewaybill.partner_bill_to_id
                )
                or ewaybill.picking_id._l10n_in_get_fiscal_position()
            )

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
            ewaybill.display_name = (
                (ewaybill.state == 'pending' and _('Pending'))
                or (ewaybill.state == 'challan' and _('Challan'))
                or ewaybill.name
            )

    @api.depends('mode')
    def _compute_vehicle_type(self):
        """when transportation mode is ship then vehicle type should be Over Dimensional Cargo (ODC)"""
        for ewaybill in self.filtered(lambda ewb: ewb.state == 'pending' and ewb.mode == "4"):
            ewaybill.vehicle_type = 'O'

    def action_export_json(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/l10n.in.ewaybill/%s/content' % self.id
        }

    def generate_ewaybill(self):
        for ewaybill in self:
            if errors := ewaybill._check_configuration():
                raise UserError('\n'.join(errors))
            ewaybill._generate_ewaybill_direct()

    def cancel_ewaybill(self):
        self.ensure_one()
        return {
            'name': _('Cancel Ewaybill'),
            'res_model': 'l10n.in.ewaybill.cancel',
            'view_mode': 'form',
            'context': {
                'default_l10n_in_ewaybill_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def reset_to_pending(self):
        self.ensure_one()
        if self.state not in ('cancel', 'challan'):
            raise UserError(_("Only Delivery Challan and Cancelled E-waybill can be reset to pending."))
        self.write({
            'name': False,
            'state': 'pending',
            'cancel_reason': False,
            'cancel_remarks': False,
        })

    def action_set_to_challan(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("The challan can only be generated in the Pending state."))
        self.write({
            'state': 'challan',
        })

    def _is_overseas(self):
        self.ensure_one()
        return self._get_gst_treatment()[1] in ('overseas', 'special_economic_zone')

    def _check_configuration(self):
        error_message = []
        methods_to_check = [
            self._check_partners,
            self._check_document_number,
            self._check_lines,
            self._check_gst_treatment,
            self._check_transporter,
        ]
        for get_error_message in methods_to_check:
            error_message.extend(get_error_message())
        return error_message

    def _check_transporter(self):
        error_message = []
        if self.transporter_id and not self.transporter_id.vat:
            error_message.append(_("- Transporter %s does not have a GST Number", self.transporter_id.name))
        if self.mode == "4" and self.vehicle_no and self.vehicle_type == "R":
            error_message.append(_("- Vehicle type can not be regular when the transportation mode is ship"))
        return error_message

    def _check_partners(self):
        error_message = []
        partners = {
            self.partner_bill_to_id, self.partner_bill_from_id, self.partner_ship_to_id, self.partner_ship_from_id
        }
        for partner in partners:
            error_message += self._l10n_in_validate_partner(partner)
        return error_message

    @api.model
    def _l10n_in_validate_partner(self, partner):
        """
        Validation method for Stock Ewaybill (different from the one in EDI Ewaybill)
        """
        message = []
        if partner.country_id.code == "IN":
            if partner.state_id and not partner.state_id.l10n_in_tin:
                message.append(_("- TIN number not set in state %s", partner.state_id.name))
            if not partner.state_id:
                message.append(_("- State is required"))
            if not partner.zip or not re.match("^[0-9]{6}$", partner.zip):
                message.append(_("- Zip code required and should be 6 digits"))
        elif not partner.country_id:
            message.append(_("- Country is required"))
        if message:
            message.insert(0, "%s" % partner.display_name)
        return message

    def _check_document_number(self):
        if not re.match("^.{1,16}$", self.document_number):
            return [_("Document number should be set and not more than 16 characters")]
        return []

    def _check_lines(self):
        error_message = []
        AccountEDI = self.env['account.edi.format']
        for line in self.move_ids:
            if not (hsn_code := AccountEDI._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code)):
                error_message.append(_("HSN code is not set in product %s", line.product_id.name))
            elif not re.match("^[0-9]+$", hsn_code):
                error_message.append(_(
                    "Invalid HSN Code (%(hsn_code)s) in product %(product)s",
                    hsn_code=hsn_code,
                    product=line.product_id.name,
                ))
        return error_message

    def _check_gst_treatment(self):
        partner, gst_treatment = self._get_gst_treatment()
        if not gst_treatment:
            return [_("Set GST Treatment for in %s", partner.display_name)]
        return []

    def _get_gst_treatment(self):
        if self.picking_type_code == 'incoming':
            partner = self.partner_bill_from_id
        else:
            partner = self.partner_bill_to_id
        return partner, partner.l10n_in_gst_treatment

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

    def _lock_ewaybill(self):
        try:
            # Lock e-Waybill
            with self.env.cr.savepoint(flush=False):
                self._cr.execute('SELECT * FROM l10n_in_ewaybill WHERE id IN %s FOR UPDATE NOWAIT', [tuple(self.ids)])
        except psycopg2.errors.LockNotAvailable:
            raise UserError(_('This document is being sent by another process already.')) from None

    def _handle_internal_warning_if_present(self, response):
        if warnings := response.get('odoo_warning'):
            for warning in warnings:
                if warning.get('message_post'):
                    odoobot = self.env.ref("base.partner_root")
                    self.message_post(
                        author_id=odoobot.id,
                        body=warning.get('message')
                    )
                else:
                    self._write_error(warning.get('message'))

    def _handle_error(self, ewaybill_error):
        self._handle_internal_warning_if_present(ewaybill_error.error_json)
        error_message = ewaybill_error.get_all_error_message()
        blocking_level = "error"
        if "404" in ewaybill_error.error_codes:
            blocking_level = "warning"
        self._write_error(error_message, blocking_level)

    def _ewaybill_cancel(self):
        cancel_json = {
            "ewbNo": int(self.name),
            "cancelRsnCode": int(self.cancel_reason),
            "CnlRem": self.cancel_remarks,
        }
        ewb_api = EWayBillApi(self.company_id)
        self._lock_ewaybill()
        try:
            ewb_api._ewaybill_cancel(cancel_json)
        except EWayBillError as error:
            self._handle_error(error)
            return False
        self._write_successfully_response({'state': 'cancel'})
        self._cr.commit()

    def _l10n_in_ewaybill_stock_handle_zero_distance_alert_if_present(self, response):
        if self.distance == 0 and (alert := response.get('data').get('alert')):
            pattern = r"Distance between these two pincodes is (\d+)"
            if (match := re.search(pattern, alert)) and (dist := int(match.group(1))) > 0:
                self.distance = dist

    def _generate_ewaybill_direct(self):
        ewb_api = EWayBillApi(self.company_id)
        generate_json = self._ewaybill_generate_direct_json()
        self._lock_ewaybill()
        try:
            response = ewb_api._ewaybill_generate(generate_json)
        except EWayBillError as error:
            self._handle_error(error)
            return False
        self._handle_internal_warning_if_present(response)  # In case of error 604
        response_data = response.get("data")
        response_values = {
            'name': response_data.get("ewayBillNo"),
            'state': 'generated',
            'ewaybill_date': self._indian_timezone_to_odoo_utc(
                response_data['ewayBillDate']
            ),
            'ewaybill_expiry_date': self._indian_timezone_to_odoo_utc(
                response_data.get('validUpto')
            ),
        }
        self._l10n_in_ewaybill_stock_handle_zero_distance_alert_if_present(response)
        self._write_successfully_response(response_values)
        self._cr.commit()

    @api.model
    def _indian_timezone_to_odoo_utc(self, str_date, time_format='%d/%m/%Y %I:%M:%S %p'):
        """
            This method is used to convert date from Indian timezone to UTC
        """
        if not str_date:
            return False
        try:
            local_time = datetime.strptime(str_date, time_format)
        except ValueError:
            try:
                # Misc. due to a bug in eWaybill sometimes there are chances of getting below format in response
                local_time = datetime.strptime(str_date, "%d/%m/%Y %H:%M:%S ")
            except ValueError:
                # Worst senario no date format matched
                _logger.warning("Something went wrong while L10nInEwaybill date conversion")
                return fields.Datetime.to_string(fields.Datetime.now())
        utc_time = local_time.astimezone(pytz.utc)
        return fields.Datetime.to_string(utc_time)

    @api.model
    def _get_partner_state_code(self, partner):
        return int(partner.state_id.l10n_in_tin) if partner.country_id.code == "IN" else 99

    def _l10n_in_tax_details(self):
        tax_details = {
            'line_tax_details': defaultdict(dict),
            'tax_details': defaultdict(float)
        }
        for move in self.move_ids:
            line_tax_vals = self._l10n_in_tax_details_by_line(move)
            tax_details['line_tax_details'][move.id] = line_tax_vals
            for val_field in ['total_excluded', 'total_included', 'total_void']:
                tax_details['tax_details'][val_field] += line_tax_vals[val_field]
            for tax in ['igst', 'cgst', 'sgst', 'cess_non_advol', 'cess', 'other']:
                for taxes in line_tax_vals['taxes']:
                    for field_key in ["rate", "amount"]:
                        if (key := f"{tax}_{field_key}") in taxes:
                            tax_details['tax_details'][key] += taxes[key]
        return tax_details

    def _l10n_in_tax_details_by_line(self, move):
        taxes = move.ewaybill_tax_ids.compute_all(price_unit=move.ewaybill_price_unit, quantity=move.quantity)
        for tax in taxes['taxes']:
            tax_id = self.env['account.tax'].browse(tax['id'])
            tax_name = "other"
            for gst_tax_name in ['igst', 'sgst', 'cgst']:
                if self.env.ref("l10n_in.tax_tag_%s" % (gst_tax_name)).id in tax['tag_ids']:
                    tax_name = gst_tax_name
            if self.env.ref("l10n_in.tax_tag_cess").id in tax['tag_ids']:
                tax_name = tax_id.amount_type != "percent" and "cess_non_advol" or "cess"
            rate_key = "%s_rate" % tax_name
            amount_key = "%s_amount" % tax_name
            tax.setdefault(rate_key, 0)
            tax.setdefault(amount_key, 0)
            tax[rate_key] += tax_id.amount
            tax[amount_key] += tax['amount']
        return taxes

    def _get_l10n_in_ewaybill_line_details(self, line, tax_details):
        AccountEDI = self.env['account.edi.format']
        product = line.product_id
        line_details = {
            "productName": product.name,
            "hsnCode": AccountEDI._l10n_in_edi_extract_digits(product.l10n_in_hsn_code),
            "productDesc": product.name,
            "quantity": line.quantity,
            "qtyUnit": line.product_uom.l10n_in_code and line.product_uom.l10n_in_code.split("-")[
                0] or "OTH",
            "taxableAmount": AccountEDI._l10n_in_round_value(tax_details['total_excluded']),
        }
        gst_types = ('sgst', 'cgst', 'igst')
        gst_tax_rates = {}
        for tax in tax_details.get('taxes'):
            for gst_type in gst_types:
                if tax_rate := tax.get(f'{gst_type}_rate'):
                    gst_tax_rates.update({
                        f"{gst_type}Rate": AccountEDI._l10n_in_round_value(tax_rate)
                    })
            if cess_rate := tax.get("cess_rate"):
                line_details.update({"cessRate": AccountEDI._l10n_in_round_value(cess_rate)})
            if cess_non_advol := tax.get("cess_non_advol_amount"):
                line_details.update({
                    "cessNonadvol": AccountEDI._l10n_in_round_value(cess_non_advol)
                })
        line_details.update(
            gst_tax_rates
            or dict.fromkeys(
                [f"{gst_type}Rate" for gst_type in gst_types],
                0
            )
        )
        return line_details

    def _prepare_ewaybill_base_json_payload(self):

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

        def prepare_details(key_paired_function, partner_detail):
            return {
                f"{place}{key}": fun(partner)
                for key, fun in key_paired_function
                for place, partner in partner_detail
            }
        ewaybill_json = {
                # document details
                "supplyType": self.supply_type,
                "subSupplyType": self.type_id.sub_type_code,
                "docType": self.type_id.code,
                "transactionType": get_transaction_type(
                    self.partner_bill_from_id,
                    self.partner_ship_from_id,
                    self.partner_bill_to_id,
                    self.partner_ship_to_id
                ),
                "transDistance": str(self.distance),
                "docNo": self.document_number,
                "docDate": (self.document_date or fields.Datetime.now()).strftime("%d/%m/%Y"),
                # bill details
                **prepare_details(
                    key_paired_function={
                        'Gstin': lambda p: p.commercial_partner_id.vat or "URP",
                        'TrdName': lambda p: p.commercial_partner_id.name,
                        'StateCode': self._get_partner_state_code,
                    }.items(),
                    partner_detail={'from': self.partner_bill_from_id, 'to': self.partner_bill_to_id}.items()
                ),
                # shipping details
                **prepare_details(
                    key_paired_function={
                        "Addr1": lambda p: p.street and p.street[:120] or "",
                        "Addr2": lambda p: p.street2 and p.street2[:120] or "",
                        "Place": lambda p: p.city and p.city[:50] or "",
                        "Pincode": lambda p: int(p.zip) if p.country_id.code == "IN" else 999999,
                    }.items(),
                    partner_detail={'from': self.partner_ship_from_id, 'to': self.partner_ship_to_id}.items()
                ),
                "actToStateCode": self._get_partner_state_code(self.partner_ship_to_id),
                "actFromStateCode": self._get_partner_state_code(self.partner_ship_from_id),
        }
        if self.type_id.sub_type_code == '8':
            ewaybill_json["subSupplyDesc"] = self.type_description
        return ewaybill_json

    def _prepare_ewaybill_transportation_json_payload(self):
        # only pass transporter details when value is exist
        return dict(
            filter(lambda kv: kv[1], {
                "transporterId": self.transporter_id.vat,
                "transporterName": self.transporter_id.name,
                "transMode": self.mode,
                "transDocNo": self.transportation_doc_no,
                "transDocDate": self.transportation_doc_date and self.transportation_doc_date.strftime("%d/%m/%Y"),
                "vehicleNo": self.vehicle_no,
                "vehicleType": self.vehicle_type,
            }.items())
        )

    def _prepare_ewaybill_tax_details_json_payload(self):
        tax_details = self._l10n_in_tax_details()
        round_value = self.env['account.edi.format']._l10n_in_round_value
        return {
            "itemList": [
                self._get_l10n_in_ewaybill_line_details(line, tax_details['line_tax_details'][line.id])
                for line in self.move_ids
            ],
            "totalValue": round_value(tax_details['tax_details'].get('total_excluded', 0.00)),
            **{
                f'{tax_type}Value': round_value(tax_details.get('tax_details').get(f'{tax_type}_amount', 0.00))
                for tax_type in ['cgst', 'sgst', 'igst', 'cess']
            },
            "cessNonAdvolValue": round_value(tax_details.get('cess_non_advol_amount', 0.00)),
            "otherValue": round_value(tax_details.get('other_amount', 0.00)),
            "totInvValue": round_value(tax_details['tax_details'].get('total_included', 0.00)),
        }

    def _ewaybill_generate_direct_json(self):
        return {
            **self._prepare_ewaybill_base_json_payload(),
            **self._prepare_ewaybill_transportation_json_payload(),
            **self._prepare_ewaybill_tax_details_json_payload(),
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_l10n_in_ewaybill_prevent(self):
        if self.filtered(lambda ewaybill: ewaybill.state != 'pending'):
            raise UserError(_("You cannot delete a generated E-waybill. Instead, you should cancel it."))
