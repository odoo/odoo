# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import pytz
import re

from datetime import datetime
from itertools import starmap

from odoo import _, api, fields, models
from odoo.exceptions import LockError, UserError
from odoo.addons.l10n_in_ewaybill.tools.ewaybill_api import EWayBillApi, EWayBillError

_logger = logging.getLogger(__name__)


class L10nInEwaybill(models.Model):

    _name = 'l10n.in.ewaybill'
    _description = "e-Waybill"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    # Ewaybill details generated from the API
    name = fields.Char("e-Waybill Number", copy=False, readonly=True, tracking=True)
    ewaybill_date = fields.Date("e-Waybill Date", copy=False, readonly=True, tracking=True)
    ewaybill_expiry_date = fields.Date("e-Waybill Valid Upto", copy=False, readonly=True, tracking=True)

    state = fields.Selection(string='Status', selection=[
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('cancel', 'Cancelled'),
    ], required=True, readonly=True, copy=False, tracking=True, default='pending')

    # Account Move details
    account_move_id = fields.Many2one('account.move', copy=False, readonly=True)

    # Document details
    document_date = fields.Datetime("Document Date", compute='_compute_ewaybill_document_details')
    document_number = fields.Char("Document", compute='_compute_ewaybill_document_details')
    company_id = fields.Many2one("res.company", compute='_compute_ewaybill_company', store=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id')
    supply_type = fields.Selection(string="Supply Type", selection=[
        ("O", "Outward"),
        ("I", "Inward")
    ], compute='_compute_supply_type')
    partner_bill_from_id = fields.Many2one(
        'res.partner',
        string='Bill From',
        compute='_compute_document_partners_details',
        check_company=True,
        store=True,
        readonly=False
    )
    partner_bill_to_id = fields.Many2one(
        'res.partner',
        string="Bill To",
        compute='_compute_document_partners_details',
        check_company=True,
        store=True,
        readonly=False
    )
    partner_ship_from_id = fields.Many2one(
        'res.partner',
        string="Dispatch From",
        compute='_compute_document_partners_details',
        check_company=True,
        store=True,
        readonly=False
    )
    partner_ship_to_id = fields.Many2one(
        'res.partner',
        string="Ship To",
        compute='_compute_document_partners_details',
        check_company=True,
        store=True,
        readonly=False
    )

    # Fields to determine which partner details are editable
    is_bill_to_editable = fields.Boolean(compute='_compute_is_editable')
    is_bill_from_editable = fields.Boolean(compute='_compute_is_editable')
    is_ship_to_editable = fields.Boolean(compute='_compute_is_editable')
    is_ship_from_editable = fields.Boolean(compute='_compute_is_editable')

    # E-waybill Document Type
    type_id = fields.Many2one('l10n.in.ewaybill.type', "Document Type", tracking=True)
    sub_type_code = fields.Char(related='type_id.sub_type_code')

    # Transportation details
    distance = fields.Integer("Distance", tracking=True)
    mode = fields.Selection([
        ('1', "By Road"),
        ('2', "Rail"),
        ('3', "Air"),
        ('4', "Ship or Ship Cum Road/Rail")
    ], string="Transportation Mode", copy=False, tracking=True, default='1')

    # Vehicle Number and Type required when transportation mode is By Road.
    vehicle_no = fields.Char("Vehicle Number", copy=False, tracking=True)
    vehicle_type = fields.Selection([
        ('R', "Regular"),
        ('O', "Over Dimensional Cargo")],
        string="Vehicle Type",
        compute='_compute_vehicle_type',
        store=True,
        copy=False,
        tracking=True,
        readonly=False
    )

    # Document number and date required in case of transportation mode is Rail, Air or Ship.
    transportation_doc_no = fields.Char(
        string="Transporter Doc No",
        copy=False,
        tracking=True
    )
    transportation_doc_date = fields.Date(
        string="Transporter Doc Date",
        copy=False,
        tracking=True
    )

    transporter_id = fields.Many2one('res.partner', "Transporter", copy=False, tracking=True)

    error_message = fields.Html(readonly=True)
    blocking_level = fields.Selection([
        ("warning", "Warning"),
        ("error", "Error")],
        string="Blocking Level", readonly=True)

    content = fields.Binary(compute='_compute_content')
    cancel_reason = fields.Selection(selection=[
        ("1", "Duplicate"),
        ("2", "Data Entry Mistake"),
        ("3", "Order Cancelled"),
        ("4", "Others"),
    ], string="Cancel reason", copy=False, tracking=True)
    cancel_remarks = fields.Char("Cancel remarks", copy=False, tracking=True)

    # Attachment
    attachment_id = fields.Many2one(
        'ir.attachment',
        compute=lambda self: self._compute_linked_attachment_id('attachment_id', 'attachment_file'),
        depends=['attachment_file'],
    )
    attachment_file = fields.Binary(copy=False, attachment=True)

    # ------------Generic compute methods to be overriden in l10n_in_ewaybill_stock module---------------

    def _get_ewaybill_dependencies(self):
        return ['account_move_id']

    def _get_ewaybill_document_details(self):
        """
        Returns document details
        :return: {'document_number': document_number, 'document_date': document_date}
        :rtype: dict
        """
        self.ensure_one()
        move = self.account_move_id
        return {
            'document_number':  move.is_purchase_document(True) and move.ref or move.name,
            'document_date': move.date
        }

    def _get_ewaybill_company(self):
        self.ensure_one()
        return self.account_move_id.company_id

    def _get_seller_buyer_details(self):
        self.ensure_one()
        move = self.account_move_id
        if move.is_outbound():
            return {
                'seller_details':  move.partner_id,
                'dispatch_details': move.partner_shipping_id or move.partner_id,
                'buyer_details': move.company_id.partner_id,
                'ship_to_details': (
                    move._l10n_in_get_warehouse_address()
                    or move.company_id.partner_id
                ),
            }
        return move._get_l10n_in_seller_buyer_party()

    def _is_incoming(self):
        self.ensure_one()
        return self.account_move_id.is_outbound()

    # -------------- Compute Methods ----------------

    def _compute_linked_attachment_id(self, attachment_field, binary_field):
        """Helper to retreive Attachment from Binary fields
        This is needed because fields.Many2one('ir.attachment') makes all
        attachments available to the user.
        """
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('res_field', '=', binary_field)
        ])
        ewb_vals = {att.res_id: att for att in attachments}
        for ewb in self:
            ewb[attachment_field] = ewb_vals.get(ewb._origin.id, False)

    @api.depends(lambda self: self._get_ewaybill_dependencies())
    def _compute_ewaybill_document_details(self):
        for ewaybill in self:
            doc_details = ewaybill._get_ewaybill_document_details()
            ewaybill.document_number = doc_details['document_number']
            ewaybill.document_date = doc_details['document_date']

    @api.depends(lambda self: self._get_ewaybill_dependencies())
    def _compute_ewaybill_company(self):
        for ewaybill in self:
            ewaybill.company_id = ewaybill._get_ewaybill_company()

    @api.depends(lambda self: self._get_ewaybill_dependencies())
    def _compute_supply_type(self):
        for ewaybill in self:
            ewaybill.supply_type = ewaybill._is_incoming() and 'I' or 'O'

    @api.depends(lambda self: self._get_ewaybill_dependencies())
    def _compute_document_partners_details(self):
        for ewaybill in self.filtered(lambda ewb: ewb.state == 'pending'):
            seller_buyer_details = ewaybill._get_seller_buyer_details()
            ewaybill.partner_bill_to_id = seller_buyer_details['buyer_details']
            ewaybill.partner_bill_from_id = seller_buyer_details['seller_details']
            ewaybill.partner_ship_to_id = seller_buyer_details['ship_to_details']
            ewaybill.partner_ship_from_id = seller_buyer_details['dispatch_details']

    @api.depends(
        'partner_ship_from_id',
        'partner_ship_to_id',
        'partner_bill_from_id',
        'partner_bill_to_id'
    )
    def _compute_is_editable(self):
        for ewaybill in self:
            if ewaybill.account_move_id:
                ewaybill.is_bill_to_editable = False
                ewaybill.is_bill_from_editable = False
                ewaybill.is_ship_from_editable = True
                ewaybill.is_ship_to_editable = True
            else:
                is_incoming = ewaybill._is_incoming()
                ewaybill.is_bill_to_editable = not is_incoming
                ewaybill.is_bill_from_editable = is_incoming
                ewaybill.is_ship_from_editable = not is_incoming
                ewaybill.is_ship_to_editable = is_incoming

    def _compute_content(self):
        dependent_fields = self._get_ewaybill_dependencies()
        for ewaybill in self:
            if any(ewaybill[d_field] for d_field in dependent_fields):
                ewaybill_json = ewaybill._ewaybill_generate_direct_json()
            else:
                ewaybill_json = {}
            ewaybill.content = base64.b64encode(json.dumps(ewaybill_json).encode())

    @api.depends('name', 'state')
    def _compute_display_name(self):
        for ewaybill in self:
            ewaybill.display_name = ewaybill.state == 'pending' and _('Pending') or ewaybill.name

    @api.depends('mode')
    def _compute_vehicle_type(self):
        """when transportation mode is ship then vehicle type should be Over Dimensional Cargo (ODC)"""
        for ewaybill in self.filtered(lambda ewb: ewb.state == 'pending' and ewb.mode == "4"):
            ewaybill.vehicle_type = 'O'

    def action_export_content_json(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/l10n.in.ewaybill/%s/content' % self.id
        }

    def action_generate_ewaybill(self):
        for ewaybill in self:
            if errors := ewaybill._check_configuration():
                raise UserError('\n'.join(errors))
            ewaybill._generate_ewaybill()

    def action_cancel_ewaybill(self):
        self.ensure_one()
        return self.env['l10n.in.ewaybill.cancel'].with_context(
            default_l10n_in_ewaybill_id=self.id
        )._get_records_action(name=_("Cancel Ewaybill"), target='new')

    def action_reset_to_pending(self):
        self.ensure_one()
        if self.state != 'cancel':
            raise UserError(_("Only Cancelled E-waybill can be resent."))
        self.write({
            'name': False,
            'state': 'pending',
            'cancel_reason': False,
            'cancel_remarks': False,
        })

    def action_print(self):
        self.ensure_one()
        if self.state in ['pending', 'cancel']:
            raise UserError(_("Please generate the E-Waybill to print it."))

        return self._generate_and_attach_pdf(_("Ewaybill"))

    @api.model
    def _get_default_help_message(self, status):
        return self.env._(
            "Somehow this E-waybill has been %s in the government portal before. "
            "You can verify by checking the details into the government "
            "(https://ewaybillgst.gov.in/Others/EBPrintnew.aspx)",
            status
        )

    def _check_configuration(self):
        error_message = []
        methods_to_check = [
            self._check_partners,
            self._check_document_number,
            self._check_lines,
            self._check_gst_treatment,
            self._check_transporter,
            self._check_state,
        ]
        for get_error_message in methods_to_check:
            error_message.extend(get_error_message())
        return error_message

    def _check_transporter(self):
        error_message = []
        transporter = self.transporter_id
        if transporter and not transporter.check_vat_in(transporter.vat) and (self.mode != "1" or not self.vehicle_no):
            error_message.append(_("- Transporter %s does not have a valid GST Number", transporter.name))
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

    def _check_state(self):
        error_message = []
        if self.account_move_id and self.account_move_id.state != 'posted':
            error_message.append(_(
                "An E-waybill cannot be generated for a %s move.",
                dict(self.env['account.move']._fields['state']._description_selection(self.env))[self.account_move_id.state]
            ))
        return error_message

    @api.model
    def _l10n_in_validate_partner(self, partner):
        """
        Validation method for Ewaybill (different from EDI)
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
        invoice_lines = self.account_move_id.invoice_line_ids
        AccountMove = self.env['account.move']
        if not any(l.product_id for l in invoice_lines):
            error_message.append(_("Ensure that at least one line item includes a product."))
            return error_message
        if all(
            AccountMove._l10n_in_is_service_hsn(l.l10n_in_hsn_code)
            for l in invoice_lines if l.product_id
        ):
            error_message.append(_("You need at least one product having 'Product Type' as stockable or consumable."))
            return error_message
        for line in invoice_lines:
            if (
                line.display_type == 'product'
                and not AccountMove._l10n_in_is_service_hsn(line.l10n_in_hsn_code)
                and (hsn_error_message := line._l10n_in_check_invalid_hsn_code())
            ):
                error_message.append(hsn_error_message)
        return error_message

    def _check_gst_treatment(self):
        partner = self._get_billing_partner()
        if not partner.l10n_in_gst_treatment:
            return [_("Set GST Treatment for in %s", partner.display_name)]
        return []

    def _get_billing_partner(self):
        if self._is_incoming():
            partner = self.partner_bill_from_id
        else:
            partner = self.partner_bill_to_id
        return partner

    def _write_error(self, error_message, blocking_level='error'):
        self.write({
            'error_message': error_message,
            'blocking_level': blocking_level,
        })

    def _write_successfully_response(self, response_vals):
        self.write({
            **response_vals,
            'error_message': False,
            'blocking_level': False,
        })

    def _lock_ewaybill(self):
        try:
            self.lock_for_update()
        except LockError:
            raise UserError(_('This document is being sent by another process already.')) from None

    def _l10n_in_ewaybill_handle_zero_distance_alert_if_present(self, response_data):
        if self.distance == 0 and (alert := response_data.get('alert')):
            pattern = r"Distance between these two pincodes is (\d+)"
            if (match := re.search(pattern, alert)) and (dist := int(match.group(1))) > 0:
                return {
                    'distance': dist
                }
        return {}

    def _handle_internal_warning_if_present(self, response):
        if warnings := response.pop('odoo_warning', False):
            for warning in warnings:
                if warning.get('message_post'):
                    self.message_post(
                        author_id=self.env.ref('base.partner_root').id,
                        body=warning.get('message')
                    )
                else:
                    self._write_error(warning.get('message'))

    def _handle_error(self, ewaybill_error):
        self._handle_internal_warning_if_present(ewaybill_error.error_json)
        error_message = ewaybill_error.get_all_error_message()
        blocking_level = 'error'
        if 'access_error' in ewaybill_error.error_codes:
            blocking_level = 'warning'
        self._write_error(error_message, blocking_level)

    def _create_and_post_response_attachment(self, ewb_name, response, is_cancel=False):
        def _create_attachment_vals(name, raw_data, res_field=False):
            vals = {
                'name': name,
                'mimetype': 'application/json',
                'raw': json.dumps(raw_data, indent=4),
                'res_model': self._name,
                'res_id': self.id,
                'res_field': res_field,
                'company_id': self.company_id.id,
            }
            return vals

        attachment_vals_list = []
        request_json = self._get_cancellation_request_vals() if is_cancel else self._ewaybill_generate_direct_json()
        request_type = 'cancel_request' if is_cancel else 'request'
        request_name = f'ewaybill_{ewb_name}_{request_type}.json'
        attachment_vals_list.append(_create_attachment_vals(request_name, request_json))
        name = f'ewaybill_{ewb_name}_cancel.json' if is_cancel else f'ewaybill_{ewb_name}.json'
        attachment_vals_list.append(_create_attachment_vals(name, response, res_field='attachment_file'))
        attachments = self.env['ir.attachment'].create(attachment_vals_list)
        self.message_post(
            author_id=self.env.ref('base.partner_root').id,
            attachment_ids=attachments.ids,
            body=self.env._("E-waybill has been successfully %s.", 'cancelled' if is_cancel else 'sent')
        )

    def _get_cancellation_request_vals(self):
        cancel_json_vals = {
            'ewbNo': int(self.name),
            'cancelRsnCode': int(self.cancel_reason),
            'cancelRmrk': self.cancel_remarks,
        }
        return cancel_json_vals

    def _ewaybill_cancel(self):
        cancel_json = self._get_cancellation_request_vals()
        ewb_api = EWayBillApi(self.company_id)
        if self.error_message and self.blocking_level == 'error':
            self.message_post(body=_(
                "Retrying to request cancellation of E-waybill on government portal."
            ))
        self._lock_ewaybill()
        try:
            response = ewb_api._ewaybill_cancel(cancel_json)
        except EWayBillError as error:
            self._handle_error(error)
            return False
        self._handle_internal_warning_if_present(response)  # In case of error 312
        self._create_and_post_response_attachment(
            ewb_name=self.name,
            response=response,
            is_cancel=True
        )
        self._write_successfully_response({'state': 'cancel'})
        self.env.cr.commit()

    def _log_retry_message_on_generate(self):
        if self.error_message and self.blocking_level == 'error':
            self.message_post(body=_(
                "Retrying E-Waybill generation on the government portal."
            ))

    def _generate_ewaybill(self):
        self.ensure_one()
        self._log_retry_message_on_generate()
        ewb_api = EWayBillApi(self.company_id)
        self._lock_ewaybill()
        try:
            response = ewb_api._ewaybill_generate(self._ewaybill_generate_direct_json())
        except EWayBillError as error:
            self._handle_error(error)
            return False
        self._handle_internal_warning_if_present(response)  # In case of error 604
        response_data = response.get('data', {})
        name = response_data.get('ewayBillNo')
        self._create_and_post_response_attachment(name, response)
        self._write_successfully_response({
            'name': name,
            'state': 'generated',
            'ewaybill_date': self._convert_str_datetime_to_date(
                response_data['ewayBillDate']
            ),
            'ewaybill_expiry_date': self._convert_str_datetime_to_date(
                response_data.get('validUpto')
            ),
            **self._l10n_in_ewaybill_handle_zero_distance_alert_if_present(response_data)
        })
        self.env.cr.commit()

    @api.model
    def _convert_str_datetime_to_date(self, str_datetime):
        """
        Expected datetime formats:
        - 25/05/2025 11:59:00 PM
        - 09/04/2025 23:59:59 (trailing with extra whitespace)
        - 2025-05-24 23:59:00
        """
        if not str_datetime:
            return False
        str_date = str_datetime[:10]  # Extract the date
        if re.match(r"\d{2}/\d{2}/\d{4}", str_date):
            return datetime.strptime(str_date, "%d/%m/%Y")
        elif re.match(r"\d{4}-\d{2}-\d{2}", str_date):
            return datetime.strptime(str_date, "%Y-%m-%d")
        _logger.error("L10nINEwaybill Invalid date format: %s", str_datetime)
        return False

    @api.model
    def _get_partner_state_code(self, partner):
        return int(partner.state_id.l10n_in_tin) if partner.country_id.code == "IN" else 99

    def _get_l10n_in_ewaybill_line_details(self, line, tax_details):
        sign = self.account_move_id.is_inbound() and -1 or 1
        extract_digits = self.env['account.move']._l10n_in_extract_digits
        round_value = self.env['account.move']._l10n_in_round_value
        tax_details_by_code = self.env['account.move']._get_l10n_in_tax_details_by_line_code(tax_details.get('tax_details', {}))
        line_details = {
            'productName': line.product_id.name[:100] if line.product_id else "",
            'hsnCode': extract_digits(line.l10n_in_hsn_code),
            'productDesc': line.name[:100] if line.name else "",
            'quantity': line.quantity,
            'qtyUnit': line.product_uom_id.l10n_in_code and line.product_uom_id.l10n_in_code.split('-')[0] or 'OTH',
            'taxableAmount': round_value(line.balance * sign),
        }
        gst_types = {'cgst', 'sgst', 'igst'}
        gst_tax_rates = {
            f"{gst_type}Rate": round_value(gst_tax_rate)
            for gst_type in gst_types
            if (gst_tax_rate := tax_details_by_code.get(f"{gst_type}_rate"))
        }
        line_details.update(
            gst_tax_rates or dict.fromkeys({f"{gst_type}Rate" for gst_type in gst_types}, 0.00)
        )
        if tax_details_by_code.get('cess_rate'):
            line_details.update({'cessRate': round_value(tax_details_by_code.get('cess_rate'))})
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
        round_value = self.env['account.move']._l10n_in_round_value
        tax_details = self.account_move_id._l10n_in_prepare_tax_details()
        tax_details_by_code = self.env['account.move']._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        invoice_line_tax_details = tax_details.get("tax_details_per_record")
        sign = self.account_move_id.is_inbound() and -1 or 1
        rounding_amount = sum(line.balance for line in self.account_move_id.line_ids if line.display_type == 'rounding') * sign
        total_invoice_value = tax_details.get("base_amount", 0.00) + tax_details.get("tax_amount", 0.00) + rounding_amount
        if self.account_move_id.l10n_in_gst_treatment == 'overseas' and self.partner_ship_to_id.country_id.code != 'IN':
            # For exports without LUT, the e-waybill total invoice value must include Reverse Charges.
            # Reverse charge amounts are stored as a negative value,
            # so we subtract it here to effectively add it to the total. (i.e. -(-x) = +x).
            adjusting_rc_amount = sum(
                tax_details_by_code.get(code, 0.00) for code in ("cgst_rc_amount", "sgst_rc_amount", "igst_rc_amount")
            )
            total_invoice_value -= adjusting_rc_amount
        return {
            "itemList": list(starmap(self._get_l10n_in_ewaybill_line_details, invoice_line_tax_details.items())),
            "totalValue": round_value(tax_details.get("base_amount", 0.00)),
            **{
                f'{tax_type}Value': round_value(tax_details_by_code.get(f'{tax_type}_amount', 0.00))
                for tax_type in ['cgst', 'sgst', 'igst', 'cess']
            },
            "cessNonAdvolValue": round_value(tax_details_by_code.get("cess_non_advol_amount", 0.00)),
            "otherValue": round_value(tax_details_by_code.get("other_amount", 0.00) + rounding_amount),
            "totInvValue": round_value(total_invoice_value),
        }

    def _ewaybill_generate_direct_json(self):
        return {
            **self._prepare_ewaybill_base_json_payload(),
            **self._prepare_ewaybill_transportation_json_payload(),
            **self._prepare_ewaybill_tax_details_json_payload(),
        }

    def _set_data_from_attachment(self):
        """
        This method is used for upgrade, to migrate the old edi_ewaybill
        In any case this method should not be removed
        see https://github.com/odoo/upgrade/pull/6624 for futher information
        """
        self.ensure_one()
        if self.attachment_id:
            try:
                res_json = json.loads(self.attachment_id.raw.decode("utf-8"))
            except ValueError:
                return False
            ewb_name = res_json.get("ewayBillNo") or res_json.get("EwbNo")
            if not ewb_name:
                return False
            ewb_date = self._convert_str_datetime_to_date(res_json.get("ewayBillDate") or res_json.get("EwbDt"))
            ewb_validity = self._convert_str_datetime_to_date(res_json.get("validUpto") or res_json.get("EwbValidTill"))
            self.write({
                "name": ewb_name,
                "ewaybill_date": ewb_date,
                "ewaybill_expiry_date": ewb_validity,
            })

    def _generate_and_attach_pdf(self, doc_label):
        self.ensure_one()
        pdf_content = self.env['ir.actions.report']._render_qweb_pdf(
            'l10n_in_ewaybill.report_ewaybill', res_ids=[self.id])[0]
        attachment = self.env['ir.attachment'].create({
            'name': f'{doc_label} - {self.document_number}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'l10n.in.ewaybill',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        self.message_post(
            body=_("%s has been generated.", doc_label),
            attachment_ids=[attachment.id]
        )
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_l10n_in_ewaybill_prevent(self):
        if self.filtered(lambda ewaybill: ewaybill.state != 'pending'):
            raise UserError(_("You cannot delete a generated E-waybill. Instead, you should cancel it."))
