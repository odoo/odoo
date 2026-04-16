# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import uuid

from odoo import _, api, fields, models, modules, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.addons.l10n_vn_edi_viettel.models.sinvoice_service import SInvoiceService


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # EDI Fields
    l10n_vn_edi_is_sent = fields.Boolean(
        string='Sent to SInvoice',
        copy=False,
        readonly=True,
    )
    l10n_vn_edi_transaction_id = fields.Char(
        string='SInvoice Transaction ID',
        help='Technical field to store the transaction ID if needed',
        export_string_translation=False,
        copy=False,
    )
    l10n_vn_edi_symbol_id = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        string='SInvoice Symbol',
        compute='_compute_l10n_vn_edi_symbol_id',
        readonly=False,
        store=True,
    )
    l10n_vn_edi_invoice_number = fields.Char(
        string='SInvoice Number',
        help='Invoice Number as appearing on SInvoice.',
        copy=False,
        readonly=True,
    )
    l10n_vn_edi_reservation_code = fields.Char(
        string='Secret Code',
        help='Secret code that can be used by a customer to lookup an invoice on SInvoice.',
        copy=False,
        readonly=True,
    )
    l10n_vn_edi_issue_date = fields.Datetime(
        string='Issue Date',
        help='Date of issue of the invoice on the e-invoicing system.',
        copy=False,
        readonly=True,
    )

    # File Fields
    l10n_vn_edi_sinvoice_file_id = fields.Many2one(
        comodel_name='ir.attachment',
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_vn_edi_sinvoice_xml_file_id = fields.Many2one(
        comodel_name='ir.attachment',
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_vn_edi_sinvoice_pdf_file_id = fields.Many2one(
        comodel_name='ir.attachment',
        copy=False,
        readonly=True,
        export_string_translation=False,
    )

    # View Fields
    l10n_vn_edi_show_send_button = fields.Boolean(
        compute='_compute_l10n_vn_edi_show_send_button',
    )

    @api.depends(
        'state',
        'location_id',
        'location_dest_id',
        'picking_type_id',
        'company_id',
        'l10n_vn_edi_is_sent',
    )
    def _compute_l10n_vn_edi_show_send_button(self):
        has_subcontracting = 'subcontractor_ids' in self.env['stock.location']._fields
        for picking in self:
            is_inter_warehouse = (
                picking.location_dest_id.usage == 'internal'
                and picking.location_dest_id.warehouse_id != picking.location_id.warehouse_id
            )
            is_subcontractor_transfer = (
                has_subcontracting
                and picking.location_dest_id.usage == 'internal'
                and picking.picking_type_id.default_location_dest_id.subcontractor_ids
            )
            is_transit = picking.location_dest_id.usage == 'transit'
            is_not_receipts = picking.picking_type_id.code != 'incoming'

            picking.l10n_vn_edi_show_send_button = (
                picking.company_id.sudo().l10n_vn_edi_send_transfer_note
                and not picking.l10n_vn_edi_is_sent
                and picking.state in ('assigned', 'done')
                and (is_inter_warehouse or is_subcontractor_transfer or is_transit)
                and is_not_receipts
            )

    @api.depends('picking_type_id', 'company_id')
    def _compute_l10n_vn_edi_symbol_id(self):
        for picking in self:
            if picking.company_id.country_id.code == 'VN':
                # Use warehouse's default symbol, fallback to company symbol if not set
                picking.l10n_vn_edi_symbol_id = (
                    picking.picking_type_id.warehouse_id.l10n_vn_edi_sinvoice_symbol_id
                    or picking.company_id.sudo().l10n_vn_edi_stock_default_sinvoice_symbol_id
                )
            else:
                picking.l10n_vn_edi_symbol_id = False

    def action_l10n_vn_send_to_sinvoice(self):
        self.ensure_one()

        # Validate config before making any API calls
        errors = self._l10n_vn_edi_check_configuration()
        if errors:
            raise UserError('\n'.join(errors))

        # Get access token
        access_token, error = self.company_id.sudo()._l10n_vn_edi_get_access_token()
        if error:
            raise UserError(error)

        # Fetch the template's custom fields from SInvoice
        template_code = self.l10n_vn_edi_symbol_id.invoice_template_code
        with SInvoiceService(access_token=access_token, vat=self.company_id.vat, env=self.env) as sinvoice:
            custom_fields, error = sinvoice.get_custom_fields(self.company_id.vat, template_code)
        if error:
            raise UserError(error)

        # Default values for well-known custom field tags
        default_values = {
            'economicContractNo': self.name,
            'exportAt': self.location_id.warehouse_id.name or '',
            'importAt': self.location_dest_id.warehouse_id.name or '',
        }

        # Create wizard pre-populated with the dynamic field lines
        wizard = self.env['l10n_vn_edi_viettel_stock.send_wizard'].create({
            'picking_id': self.id,
            'template_field_ids': [
                (0, 0, {
                    'key_tag': f['keyTag'],
                    'key_label': f['keyLabel'],
                    'value_type': f.get('valueType', 'text'),
                    'is_required': f.get('isRequired', False),
                    'is_seller': f.get('isSeller', False),
                    'value': default_values.get(f['keyTag'], ''),
                })
                for f in custom_fields
            ],
        })

        return {
            'name': _('Send to SInvoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l10n_vn_edi_viettel_stock.send_wizard',
            'res_id': wizard.id,
            'target': 'new',
        }

    # =========================================================================
    # EDI LOGIC
    # =========================================================================

    def _l10n_vn_edi_check_configuration(self):
        """Return a list of error messages if the picking is not properly configured for SInvoice."""
        self.ensure_one()
        errors = []
        company = self.company_id
        if not company._l10n_vn_edi_get_credentials_company():
            errors.append(_('SInvoice credentials are missing on company %s.', company.display_name))
        if not company.vat:
            errors.append(_('VAT number is missing on company %s.', company.display_name))
        if not self.l10n_vn_edi_symbol_id:
            errors.append(_('The transfer note symbol must be provided. Set it on the warehouse or in the Inventory settings.'))
        if self.l10n_vn_edi_symbol_id and not self.l10n_vn_edi_symbol_id.invoice_template_code:
            errors.append(_("The symbol's template code must be provided."))
        if not company.street or not company.country_id:
            errors.append(_('The street and country of company %s must be provided.', company.display_name))
        return errors

    def _l10n_vn_edi_generate_transfer_note_json(self, template_field_lines=None):
        """Return the dict of data that will be sent to the API to create the transfer note."""
        self.ensure_one()
        self.l10n_vn_edi_issue_date = fields.Datetime.now()
        json_values = {}
        self._l10n_vn_edi_add_general_info(json_values)
        self._l10n_vn_edi_add_buyer_info(json_values)
        self._l10n_vn_edi_add_seller_info(json_values)
        self._l10n_vn_edi_add_item_info(json_values)
        self._l10n_vn_edi_add_tax_breakdowns(json_values)
        self._l10n_vn_edi_add_payment_information(json_values)
        self._l10n_vn_edi_add_metadata(json_values, template_field_lines or [])
        return json_values

    def _l10n_vn_edi_add_general_info(self, json_values):
        self.ensure_one()
        json_values['generalInvoiceInfo'] = {
            'transactionUuid': str(uuid.uuid4()),
            'templateCode': self.l10n_vn_edi_symbol_id.invoice_template_code,
            'invoiceSeries': self.l10n_vn_edi_symbol_id.name,
            'invoiceIssuedDate': SInvoiceService.format_date(self.l10n_vn_edi_issue_date),
            'currencyCode': self.company_id.currency_id.name or 'VND',
            'adjustmentType': '1',
            'paymentStatus': True,
            'cusGetInvoiceRight': True,
        }

    def _l10n_vn_edi_add_buyer_info(self, json_values):
        self.ensure_one()
        if partner := self.partner_id:
            phone = partner.phone and SInvoiceService.format_phone_number(partner.phone) or ''
            buyer_address = self.partner_id._display_address(without_name=True, separator=', ')
            json_values['buyerInfo'] = {
                'buyerName': partner.name or '',
                'buyerLegalName': partner.commercial_partner_id.name or '',
                'buyerTaxCode': partner.commercial_partner_id.vat or '',
                'buyerAddressLine': buyer_address or '',
                'buyerPhoneNumber': phone,
                'buyerEmail': partner.email or '',
                'buyerCityName': partner.city or partner.state_id.name or '',
                'buyerCountryCode': partner.country_id.code or '',
            }
        else:
            json_values['buyerInfo'] = {'buyerNotGetInvoice': 1}

    def _l10n_vn_edi_add_seller_info(self, json_values):
        self.ensure_one()
        company = self.company_id
        phone = company.phone and SInvoiceService.format_phone_number(company.phone) or ''
        seller_address = company.partner_id._display_address(without_name=True, separator=', ')
        json_values['sellerInfo'] = {
            'sellerLegalName': company.name,
            'sellerTaxCode': company.vat,
            'sellerAddressLine': seller_address or '',
            'sellerPhoneNumber': phone,
            'sellerEmail': company.email or '',
            'sellerDistrictName': company.state_id.name or '',
            'sellerCountryCode': company.country_id.code or '',
        }

    def _l10n_vn_edi_add_item_info(self, json_values):
        self.ensure_one()
        items = []
        for move in self.move_ids:
            qty = move.product_uom_qty if self.state == 'draft' else move.quantity
            if not qty:
                continue
            unit_price = move.l10n_vn_edi_unit_price
            items.append({
                'itemCode': move.product_id.default_code or '',
                'itemName': move.product_id.name,
                'unitName': move.product_id.uom_name or 'Unit',
                'unitPrice': unit_price,
                'quantity': qty,
                'itemTotalAmountWithoutTax': self.company_id.currency_id.round(unit_price * qty),
                'taxPercentage': -2,  # No tax for internal transfer notes
                'taxAmount': 0,
            })
        json_values['itemInfo'] = items

    def _l10n_vn_edi_add_tax_breakdowns(self, json_values):
        """Tax breakdown for transfer notes; no tax applies for stock picking."""
        self.ensure_one()
        total_amount = sum(item['itemTotalAmountWithoutTax'] for item in json_values.get('itemInfo', []))
        json_values['taxBreakdowns'] = [{
            'taxPercentage': -2,  # -2 means no tax
            'taxableAmount': total_amount,
            'taxAmount': 0,
            'taxableAmountPos': True,
            'taxAmountPos': True,
        }]

    def _l10n_vn_edi_add_payment_information(self, json_values):
        self.ensure_one()
        json_values['payments'] = [{
            # We need to provide a value but when we send the invoice, we may not have this information.
            # According to VN laws, if the payment method has not been determined, we can fill in TM/CK.
            # TM is for bank transfer, CK is for cash payment.
            'paymentMethodName': 'TM/CK',
        }]

    def _l10n_vn_edi_add_metadata(self, json_values, template_field_lines):
        self.ensure_one()
        metadata = []
        for line in template_field_lines:
            if line.value or line.is_required:
                metadata.append({
                    'keyTag': line.key_tag,
                    'stringValue': line.value or '',
                    'valueType': line.value_type,
                    'keyLabel': line.key_label,
                    'isRequired': line.is_required,
                    'isSeller': line.is_seller,
                })
        json_values['metadata'] = metadata

    def _l10n_vn_edi_send_transfer_note(self, json_data):
        """Send the transfer note to SInvoice. Returns a list of error messages."""
        self.ensure_one()
        self.env['res.company']._with_locked_records(self)

        access_token, error = self.company_id.sudo()._l10n_vn_edi_get_access_token()
        if error:
            return [error]

        with SInvoiceService(access_token=access_token, vat=self.company_id.vat, env=self.env) as sinvoice:
            invoice_data = {}
            if self.l10n_vn_edi_transaction_id:
                lookup, _err = sinvoice.lookup_invoice(self.l10n_vn_edi_transaction_id)
                if 'result' in lookup:
                    invoice_data = lookup['result'][0]

            if not invoice_data:
                self.l10n_vn_edi_transaction_id = json_data['generalInvoiceInfo']['transactionUuid']
                if not modules.module.current_test:
                    self.env.cr.commit()
                invoice_data, error_message = sinvoice.create_invoice(json_data)
                if error_message:
                    if 'BAD_REQUEST_STRING_VALUE_INFO_UPDATE_REQUIRED' in error_message:
                        error_message = _('Some required template fields are missing or have invalid values. Please check the required template fields and try again.')
                    return [error_message]

        self.write({
            'l10n_vn_edi_reservation_code': invoice_data.get('reservationCode'),
            'l10n_vn_edi_invoice_number': invoice_data.get('invoiceNo'),
            'l10n_vn_edi_is_sent': True,
        })

        return []

    def l10n_vn_edi_fetch_files(self):
        """Public entry point for the 'Fetch SInvoice Files' server action."""
        self.ensure_one()
        errors = self._l10n_vn_edi_fetch_files()
        if errors:
            error_msg = '{}\n{}'.format(errors['error_title'], '\n'.join(errors['errors']))
            raise UserError(error_msg)

    def _l10n_vn_edi_fetch_files(self):
        """Fetch XML and PDF files from SInvoice and attach them to this picking."""
        self.ensure_one()
        if not self.l10n_vn_edi_is_sent:
            raise UserError(_("Please send the transfer note to SInvoice before fetching the files."))

        access_token, error = self.company_id._l10n_vn_edi_get_access_token()
        if error:
            return {'error_title': _('Cannot get access token.'), 'errors': [error]}

        template_code = self.l10n_vn_edi_symbol_id.invoice_template_code
        invoice_no = self.l10n_vn_edi_invoice_number
        xml_data = xml_error = pdf_data = pdf_error = None

        with SInvoiceService(access_token=access_token, vat=self.company_id.vat, env=self.env) as sinvoice:
            zip_data, zip_error = sinvoice.get_invoice_file(template_code, invoice_no, 'ZIP')
            if zip_error:
                xml_error = zip_error
            else:
                if file_bytes := zip_data.get('fileToBytes'):
                    xml_data, xml_error = sinvoice.extract_xml_from_zip(
                        base64.b64decode(file_bytes)
                    )
                else:
                    xml_error = _('XML file not yet available from Viettel.')

                if xml_data:
                    xml_data['res_field'] = 'l10n_vn_edi_sinvoice_xml_file_id'

            pdf_file_data, pdf_error = sinvoice.get_invoice_file(template_code, invoice_no, 'PDF')
            if not pdf_error and pdf_file_data.get('fileToBytes'):
                pdf_data = {
                    'name': pdf_file_data['fileName'],
                    'mimetype': 'application/pdf',
                    'raw': base64.b64decode(pdf_file_data['fileToBytes']),
                    'res_field': 'l10n_vn_edi_sinvoice_pdf_file_id',
                }

        attachments_data = []
        for file, err in [(xml_data, xml_error), (pdf_data, pdf_error)]:
            if err or not file:
                continue
            attachments_data.append({
                'name': file['name'],
                'raw': file['raw'],
                'mimetype': file['mimetype'],
                'res_model': self._name,
                'res_id': self.id,
                'res_field': file['res_field'],
            })

        if attachments_data:
            attachments = self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachments_data)
            for att in attachments:
                self[att.res_field] = att.id
            self.message_post(
                body=_('Transfer note sent to SInvoice'),
                attachment_ids=attachments.ids + self.l10n_vn_edi_sinvoice_file_id.ids,
            )

        if xml_error or pdf_error:
            return {
                'error_title': _('Error when receiving SInvoice files.'),
                'errors': [e for e in [xml_error, pdf_error] if e],
            }
