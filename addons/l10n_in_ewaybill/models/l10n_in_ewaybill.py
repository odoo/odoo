# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import pytz
import re

import psycopg2.errors

from datetime import datetime
from itertools import starmap

from odoo import _, api, fields, models
from odoo.exceptions import UserError
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

    content = fields.Binary(compute='_compute_content', compute_sudo=True)
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
            'document_number':  self._is_incoming() and move.ref or move.name,
            'document_date': move.date
        }

    def _get_ewaybill_company(self):
        self.ensure_one()
        return self.account_move_id.company_id

    def _get_seller_buyer_details(self):
        self.ensure_one()
        return self.account_move_id._get_l10n_in_seller_buyer_party()

    def _is_incoming(self):
        self.ensure_one()
        return self.account_move_id.is_purchase_document(include_receipts=True)

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
            is_incoming = ewaybill._is_incoming()
            is_overseas = (
                ewaybill._get_billing_partner().l10n_in_gst_treatment in ('overseas', 'special_economic_zone')
            )
            ewaybill.is_bill_to_editable = not is_incoming
            ewaybill.is_bill_from_editable = is_incoming
            ewaybill.is_ship_from_editable = is_incoming and is_overseas
            ewaybill.is_ship_to_editable = not is_incoming and not is_overseas

    def _compute_content(self):
        for ewaybill in self:
            ewaybill_json = ewaybill._ewaybill_generate_direct_json()
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
        if not any(l.product_id for l in invoice_lines):
            error_message.append(_("Ensure that at least one line item includes a product."))
            return error_message
        if all(l.product_id.type == 'service' for l in invoice_lines if l.product_id):
            error_message.append(_("You need at least one product having 'Product Type' as stockable or consumable."))
            return error_message
        for line in invoice_lines:
            if (
                line.display_type == 'product'
                and line.product_id.type != 'service'
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
            # Lock e-Waybill
            with self.env.cr.savepoint(flush=False):
                self._cr.execute('SELECT * FROM l10n_in_ewaybill WHERE id IN %s FOR UPDATE NOWAIT', [tuple(self.ids)])
        except psycopg2.errors.LockNotAvailable:
            raise UserError(_('This document is being sent by another process already.')) from None

    def _l10n_in_ewaybill_handle_zero_distance_alert_if_present(self, response_data):
        if self.distance == 0 and (alert := response_data.get('alert')):
            pattern = r", Distance between these two pincodes is \d+, "
            if re.fullmatch(pattern, alert) and (dist := int(re.search(r'\d+', alert).group())) > 0:
                return {
                    'distance': dist
                }
        return {}

    def _handle_internal_warning_if_present(self, response):
        if warnings := response.get('odoo_warning'):
            for warning in warnings:
                if warning.get('message_post'):
                    odoobot = self.env.ref('base.partner_root')
                    self.message_post(
                        author_id=odoobot.id,
                        body=warning.get('message')
                    )
                else:
                    self._write_error(warning.get('message'))

    def _handle_error(self, ewaybill_error):
        self._handle_internal_warning_if_present(ewaybill_error.error_json)
        error_message = ewaybill_error.get_all_error_message()
        blocking_level = 'error'
        if '404' in ewaybill_error.error_codes:
            blocking_level = 'warning'
        self._write_error(error_message, blocking_level)

    def _create_and_post_response_attachment(self, ewb_name, response, is_cancel=False):
        if not is_cancel:
            name = f'ewaybill_{ewb_name}.json'
        else:
            name = f'ewaybill_{ewb_name}_cancel.json'
        attachment = self.env['ir.attachment'].create({
            'name': name,
            'mimetype': 'application/json',
            'raw': json.dumps(response),
            'res_model': self._name,
            'res_id': self.id,
            'res_field': 'attachment_file',
            'company_id': self.company_id.id
        })
        self.message_post(
            author_id=self.env.ref('base.partner_root').id,
            attachment_ids=attachment.ids
        )

    def _ewaybill_cancel(self):
        cancel_json = {
            'ewbNo': int(self.name),
            'cancelRsnCode': int(self.cancel_reason),
            'CnlRem': self.cancel_remarks,
        }
        ewb_api = EWayBillApi(self.company_id)
        self._lock_ewaybill()
        try:
            response = ewb_api._ewaybill_cancel(cancel_json)
        except EWayBillError as error:
            self._handle_error(error)
            return False
        self._create_and_post_response_attachment(
            ewb_name=self.name,
            response=response,
            is_cancel=True
        )
        self._write_successfully_response({'state': 'cancel'})
        self._cr.commit()

    def _generate_ewaybill(self):
        self.ensure_one()
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
            'ewaybill_date': self._indian_timezone_to_odoo_utc(
                response_data['ewayBillDate']
            ),
            'ewaybill_expiry_date': self._indian_timezone_to_odoo_utc(
                response_data.get('validUpto')
            ),
            **self._l10n_in_ewaybill_handle_zero_distance_alert_if_present(response_data)
        })
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

    def _get_l10n_in_ewaybill_line_details(self, line, tax_details):
        sign = self.account_move_id.is_inbound() and -1 or 1
        extract_digits = self.env['account.move']._l10n_in_extract_digits
        round_value = self.env['account.move']._l10n_in_round_value
        tax_details_by_code = self.env['account.move']._get_l10n_in_tax_details_by_line_code(tax_details.get('tax_details', {}))
        line_details = {
            'productName': line.product_id.name or line.name,
            'hsnCode': extract_digits(line.l10n_in_hsn_code),
            'productDesc': line.product_id.display_name,
            'quantity': line.quantity,
            'qtyUnit': line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split('-')[0] or 'OTH',
            'taxableAmount': round_value(line.balance * sign),
        }
        if tax_details_by_code.get('igst_rate') or (line.move_id.l10n_in_state_id.l10n_in_tin != line.company_id.state_id.l10n_in_tin):
            line_details.update({'igstRate': round_value(tax_details_by_code.get('igst_rate', 0.00))})
        else:
            line_details.update({
                'cgstRate': round_value(tax_details_by_code.get('cgst_rate', 0.00)),
                'sgstRate': round_value(tax_details_by_code.get('sgst_rate', 0.00)),
            })
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
                "docDate": self.document_date.strftime("%d/%m/%Y"),
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
        return {
            "itemList": list(starmap(self._get_l10n_in_ewaybill_line_details, invoice_line_tax_details.items())),
            "totalValue": round_value(tax_details.get("base_amount", 0.00)),
            **{
                f'{tax_type}Value': round_value(tax_details_by_code.get(f'{tax_type}_amount', 0.00))
                for tax_type in ['cgst', 'sgst', 'igst', 'cess']
            },
            "cessNonAdvolValue": round_value(tax_details_by_code.get("cess_non_advol_amount", 0.00)),
            "otherValue": round_value(tax_details_by_code.get("other_amount", 0.00)),
            "totInvValue": round_value(tax_details.get("base_amount", 0.00) + tax_details.get("tax_amount", 0.00)),
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
            ewb_date = self._indian_timezone_to_odoo_utc(res_json.get("ewayBillDate") or res_json.get("EwbDt"))
            ewb_validity = self._indian_timezone_to_odoo_utc(res_json.get("validUpto") or res_json.get("EwbValidTill"))
            self.write({
                "name": ewb_name,
                "ewaybill_date": ewb_date,
                "ewaybill_expiry_date": ewb_validity,
            })

    @api.ondelete(at_uninstall=False)
    def _unlink_l10n_in_ewaybill_prevent(self):
        if self.filtered(lambda ewaybill: ewaybill.state != 'pending'):
            raise UserError(_("You cannot delete a generated E-waybill. Instead, you should cancel it."))
