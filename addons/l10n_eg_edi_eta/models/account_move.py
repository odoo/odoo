# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import requests

from json import JSONDecodeError
from werkzeug.urls import url_encode
from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, BinaryBytes
from odoo.tools.float_utils import json_float_round
from odoo.addons.account.tools import LegacyHTTPAdapter
from odoo.addons.l10n_eg_edi_eta.models.eta_submission import ETA_SUBMISSION_STATES


ETA_INVOICE_SENDING_BATCH_SIZE = 10

ETA_DOMAINS = {
    'demo': 'https://api.preprod.invoicing.eta.gov.eg',
    'production': 'https://api.invoicing.eta.gov.eg',
    'invoice.demo': 'https://preprod.invoicing.eta.gov.eg/',
    'invoice.production': 'https://invoicing.eta.gov.eg',
    'token.demo': 'https://id.preprod.eta.gov.eg',
    'token.production': 'https://id.eta.gov.eg',
}

ETA_INVOICE_SUBMISSION_STATES = ETA_SUBMISSION_STATES + [('to_send', 'To Send')]

ETA_DUMMY_SUBMISSION_ID = "TZRKK8MFZ CPSTW9XC YWBMKME10A BC123160 2681697"

ETA_INVOICE_DUMMY_RESPONSE = {
    'uuid': 'TZRKK8MFZCPSTW9XCYWBMKME11',
    'longId': 'TZRKK8MFZ CPSTW9XC YWBMKME10A BC123160 2681697',
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_eg_long_id = fields.Char(string='ETA Long ID', compute='_compute_eta_long_id')
    l10n_eg_qr_code = fields.Char(string='ETA QR Code', compute='_compute_eta_qr_code_str')
    l10n_eg_uuid = fields.Char(
        string='Document UUID',
        compute='_compute_l10n_eg_edi_uuid',
        store=True,
        copy=False,
        init_storage=lambda model: None
    )
    l10n_eg_eta_json_doc_file = fields.Binary(
        string='ETA JSON Document',
        attachment=True,
        copy=False,
    )
    l10n_eg_eta_submission_ids = fields.One2many(
        'l10n_eg_edi.eta.submission',
        'move_id',
        string='ETA Submissions',
        copy=False,
    )
    l10n_eg_edi_api_mode = fields.Selection(related='company_id.l10n_eg_edi_api_mode', string='ETA Mode')
    l10n_eg_edi_submission_state = fields.Selection(
        selection=ETA_INVOICE_SUBMISSION_STATES,
        string="ETA State",
        compute='_compute_l10n_eg_edi_submission_values',
        store=True,
    )
    l10n_eg_edi_message = fields.Char(
        string="ETA Response",
        compute='_compute_l10n_eg_edi_submission_values',
        store=True,
    )
    l10n_eg_signing_time = fields.Datetime('Signing Time', copy=False)
    l10n_eg_is_signed = fields.Boolean("Is Signed", copy=False)
    l10n_eg_cancel_reason = fields.Char("ETA Reason", copy=False)

    @api.depends('l10n_eg_uuid', 'l10n_eg_long_id')
    def _compute_eta_qr_code_str(self):
        for move in self:
            if move.l10n_eg_uuid and move.l10n_eg_long_id and move.l10n_eg_edi_api_mode != 'demo':
                is_production = move.l10n_eg_edi_api_mode == 'production'
                base_url = self._l10n_eg_get_eta_qr_domain(is_production=is_production)
                qr_code_str = '%s/documents/%s/share/%s' % (base_url, move.l10n_eg_uuid, move.l10n_eg_long_id)
                move.l10n_eg_qr_code = qr_code_str
            else:
                move.l10n_eg_qr_code = ''

    @api.depends('l10n_eg_eta_submission_ids')
    def _compute_eta_long_id(self):
        for move in self:
            last_submission = move.l10n_eg_eta_submission_ids and move.l10n_eg_eta_submission_ids[-1]
            if last_submission:
                move.l10n_eg_long_id = last_submission.eta_document_longid
            else:
                move.l10n_eg_long_id = False

    @api.depends('l10n_eg_eta_submission_ids', 'state')
    def _compute_l10n_eg_edi_submission_values(self):
        for move in self:
            last_submission = move.l10n_eg_eta_submission_ids and move.l10n_eg_eta_submission_ids[-1]
            if last_submission:
                move.l10n_eg_edi_submission_state = last_submission.state
                move.l10n_eg_edi_message = last_submission.message
            else:
                move.l10n_eg_edi_submission_state = move.state == 'posted' and 'to_send' or False
                move.l10n_eg_edi_message = ''

    @api.depends('l10n_eg_eta_submission_ids')
    def _compute_l10n_eg_edi_uuid(self):
        for move in self:
            move.l10n_eg_uuid = (
                move.l10n_eg_eta_submission_ids
                and move.l10n_eg_eta_submission_ids[-1].eta_document_uuid
                or False
            )

    @api.depends('l10n_eg_eta_submission_ids')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if (
                move.country_code == 'EG'
                and move.state == 'posted'
                and (move.l10n_eg_edi_api_mode != 'production'
                or not move.l10n_eg_eta_submission_ids
                or move.l10n_eg_edi_submission_state == 'rejected'
            )):
                move.show_reset_to_draft_button = True

    def button_draft(self):
        self.l10n_eg_is_signed = False
        return super().button_draft()

    def action_l10n_eg_cancel_invoice(self):
        eg_moves = self.filtered(
            lambda m: m.country_code == 'EG' and m.l10n_eg_edi_submission_state in ['accepted', 'test'] and m.state == 'posted'
        )
        if not eg_moves:
            self.env.user._bus_send('simple_notification', {
                "type": "warning",
                "message": self.env._("No valid Egyptian invoices found for cancellation."),
                "sticky": True,
            })
            return

        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("ETA Cancel"),
            'res_model': 'l10n_eg_edi.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_ids': eg_moves.ids,
            },
        }

    def action_get_eta_invoice_pdf(self):
        """ This is a pdf with the structure from the government. While we can use our own format,
        some clients appreciate this to verify that all the data is there in case of confusion."""
        eg_moves = self.filtered(
            lambda m: m.country_code == 'EG' and m.l10n_eg_edi_submission_state in ['accepted', 'test'] and m.state == 'posted'
        )
        if not eg_moves:
            self.env.user._bus_send('simple_notification', {
                "type": "info",
                "message": self.env._("No valid Egyptian invoices found for fetching PDFs."),
                "sticky": True,
            })
            return

        if eg_moves.company_id.filtered(lambda c: c.l10n_eg_edi_api_mode == 'demo'):
            raise UserError(self.env._("Cannot fetch PDF if the invoice company's ETA API mode is in Demo."))

        access_data = self._l10n_eg_eta_get_access_token()
        if access_data.get('error'):
            raise UserError(self.env._("Failed to authenticate with the ETA server. Are the credentials correct?"))

        access_token = access_data.get('access_token')
        moves_failed_to_fetch = self.env['account.move']
        for move in eg_moves:
            if not move._l10n_eg_get_eta_invoice_pdf(access_token):
                moves_failed_to_fetch |= move

        action_to_return = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': (
                    moves_failed_to_fetch and self.env._("Failed to fetch PDFs for some invoice(s)")
                    or self.env._("PDFs fetched successfully from ETA.")
                ),
                'type': moves_failed_to_fetch and 'warning' or 'success',
                'sticky': True,
            },
        }
        if moves_failed_to_fetch:
            action_to_return['params'].update(
                {'next': moves_failed_to_fetch._get_records_action(name=self.env._("PDFs not fetched"))}
            )
        return action_to_return

    def action_post_sign_invoices(self):
        invoices = self.filtered(lambda i: (
            i.country_code == 'EG'
            and i.state == 'posted'
            and i.l10n_eg_edi_submission_state not in ['test', 'accepted']
        ))
        if not invoices:
            return

        # since the middleware accepts only one drive at a time, we have to limit signing to one company at a time.
        company = invoices.company_id
        if len(company.ids) > 1:
            raise UserError(self.env._("Please only sign invoices from one company at a time."))

        drive_id = self.env['l10n_eg_edi.thumb.drive'].search(
            [('user_id', '=', self.env.user.id), ('company_id', '=', company.id)], limit=1
        )

        if not drive_id and company.l10n_eg_edi_api_mode != 'demo':
            raise ValidationError(self.env._('Please setup a personal drive for company %s', company.name))

        if not drive_id.certificate and company.l10n_eg_edi_api_mode != 'demo':
            raise ValidationError(self.env._('Please setup the certificate on the thumb drive menu'))

        signing_time = fields.Datetime.now()
        invoices.write({'l10n_eg_signing_time': signing_time})

        is_demo = company.l10n_eg_edi_api_mode == 'demo'
        attachments_to_create = []
        invoices_to_sign = {}
        for invoice in invoices:
            einvoice_json = invoice._generate_l10n_eg_edi_json(is_demo)
            attachments_to_create.append({
                'name': self.env._('ETA_INVOICE_DOC_%s', invoice.name),
                'res_id': invoice.id,
                'res_model': invoice._name,
                'res_field': 'l10n_eg_eta_json_doc_file',
                'raw': json.dumps(dict(request=einvoice_json)).encode(),
                'mimetype': 'application/json',
            })
            if not is_demo:
                invoices_to_sign[invoice.id] = {'invoice': einvoice_json, 'signing_time': signing_time}
            else:
                invoice.l10n_eg_is_signed = True
                invoice.message_post(body=self.env._("Success: Invoice signed for ETA"))

        self.env['ir.attachment'].create(attachments_to_create)
        self.invalidate_recordset(fnames=['l10n_eg_eta_json_doc_file'])

        if invoices_to_sign:
            return drive_id.action_sign_invoices(invoices_to_sign)

    def _get_fields_to_detach(self):
        fields_list = super()._get_fields_to_detach()
        fields_list.append('l10n_eg_eta_json_doc_file')
        return fields_list

    def _l10n_eg_eta_qr_code(self):
        if self.l10n_eg_edi_submission_state in ['test', 'accepted']:
            url_params = url_encode({
                'barcode_type': 'QR',
                'value': self.l10n_eg_qr_code or '',
                'width': 130,
                'height': 130,
                'quiet': 0,
            })
            return f'/report/barcode/?{url_params}'

    def l10n_eg_log_on_sign_failure(self):
        """Method called from client side when signing with thumb drive fails."""
        self.message_post(
            body=self.env._("Error: Invoice could not be signed.\nCannot connect to the middleware")
        )

    # ===================================================
    # Account move send validations
    # ===================================================

    def _get_l10n_eg_edi_alerts(self):
        alerts = {}

        if (companies := self.company_id) and len(companies) > 1:
            alerts.update({
                'eg_eta_edi_multiple_companiesbranch partner': {
                    'level': 'danger',
                    'message': self.env._(
                        """Only invoices from one company can be signed at a time.
                        Please select invoices from a single company to sign and send to ETA.""",
                    ),
                },
            })
        elif companies.l10n_eg_edi_api_mode != 'demo' and (
            not companies.l10n_eg_client_identifier or not companies.l10n_eg_client_secret
        ):
            alerts.update({
                'eg_eta_edi_no_client_id_secret': {
                    'level': 'danger',
                    'message': self.env._(
                        "Please configure Client ID and Secret Key for the company %s.",
                        companies[0].name,
                    ),
                },
            })

        if missing_branch_details := self.journal_id.l10n_eg_branch_id.filtered(
            lambda p: p._check_l10n_eg_missing_address_data()
        ):
            alerts.update({
                'eg_eta_edi_missing_company_address': {
                    'level': 'danger',
                    'message': self.env._("Please fill in the address details for the following Journal Branches"),
                    'action_text': self.env._("view branches"),
                    'action': missing_branch_details._get_records_action(),
                },
            })

        if missing_partner_address := self.partner_id.filtered(lambda p: p._check_l10n_eg_missing_address_data()):
            alerts.update({
                'eg_eta_edi_missing_partner_address': {
                    'level': 'danger',
                    'message': self.env._("Please fill in the address details for the following partners."),
                    'action_text': self.env._("View Partners"),
                    'action': missing_partner_address._get_records_action(),
                },
            })

        if moves_without_journal_config := self.filtered(
            lambda m: not (
                m.journal_id.l10n_eg_branch_id
                and m.journal_id.l10n_eg_activity_type_id
                and m.journal_id.l10n_eg_branch_identifier
            ),
        ):
            alerts.update({
                'eg_eta_edi_journal_not_configured': {
                    'level': 'danger',
                    'message': self.env._(
                        "Please configure Egyptian ETA Settings on the Journal(s).",
                    ),
                    'action_text': self.env._("View Journals"),
                    'action': moves_without_journal_config.journal_id._get_records_action(),
                },
            })

        if moves_with_future_date := self.filtered(
            lambda m: m.invoice_date > fields.Datetime.now().date()
        ):
            alerts.update({
                'eg_eta_edi_moves_with_future_dates': {
                    'level': 'danger',
                    'message': self.env._(
                        "Please set the invoice date to be either less than or equal to today.",
                    ),
                    'action_text': self.env._("View Invoices"),
                    'action': moves_with_future_date._get_records_action(),
                }
            })

        amls_to_check = self.invoice_line_ids.filtered(
            lambda l: l.display_type not in {'line_section', 'line_subsection', 'line_note'}
        )

        if amls_without_tax := amls_to_check.filtered(lambda l: not l.tax_ids):
            alerts.update({
                'eg_eta_edi_no_tax_lines': {
                    'level': 'danger',
                    'message': self.env._(
                        "Please make sure that there is tax in each invoice lines.",
                    ),
                    'action_text': self.env._("View Invoices"),
                    'action': amls_without_tax._get_records_action(),
                },
            })

        if lines_without_product := amls_to_check.filtered(lambda l: not l.product_id):
            alerts.update({
                'eg_eta_edi_lines_without_product': {
                    'level': 'danger',
                    'message': self.env._(
                        "Please make sure that following invoice lines have a product in them.",
                    ),
                    'action_text': self.env._("View Invoices"),
                    'action': lines_without_product.move_id._get_records_action(),
                },
            })

        if invalid_line_names := amls_to_check.filtered(lambda l: len(l.name or '') > 500):
            alerts.update({
                'eg_eta_edi_lines_with_invalid_name': {
                    'level': 'danger',
                    'message': self.env._("""
                        The product description exceeds the ETA limit of 500 characters (including spaces) for some
                        invoice lines. Please shorten the description and try again.
                    """),
                    'action_text': self.env._("View Products"),
                    'action': invalid_line_names._get_records_action(),
                }
            })

        if products_without_code := amls_to_check.product_id.filtered(lambda p: not (p.l10n_eg_eta_code or p.barcode)):
            alerts.update({
                'eg_eta_edi_lines_without_product': {
                    'level': 'danger',
                    'message': self.env._(
                        "Please make sure that following products have barcode or ETA Item code set on them.",
                    ),
                    'action_text': self.env._("View Products"),
                    'action': products_without_code._get_records_action(),
                },
            })

        if unsigned_moves := self.filtered(lambda m: not m.l10n_eg_is_signed):
            alerts.update({
                'eg_eta_edi_moves_not_signed': {
                    'level': 'danger',
                    'message': self.env._("Invoice needs to be signed before ETA submission."),
                    'action_text': self.env._("View Invoices"),
                    'action': unsigned_moves._get_records_action(),
                }
            })

        return alerts

    # ===================================================
    #   EDI Helper Methods
    # ===================================================

    def _l10n_eg_edi_exchange_currency_rate(self):
        """ Calculate the rate based on the balance and amount_currency, so we recuperate the one used at the time"""
        self.ensure_one()
        from_currency = self.currency_id
        to_currency = self.company_id.currency_id
        if from_currency != to_currency and self.invoice_line_ids:
            first_product_line = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")[:1]
            amount_currency = first_product_line.amount_currency
            if not float_is_zero(amount_currency, precision_rounding=from_currency.rounding):
                # The `balance` on an invoice line is a rounded value, calculated using the invoice_currency_rate.
                # To avoid rounding discrepancies, the rate is recalculated from this final rounded balance instead of
                # directly using invoice_currency_rate.
                return abs(first_product_line.balance / amount_currency)
        return 1.0

    def _l10n_eg_edi_round(self, amount, precision_digits=5):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        return json_float_round(amount, precision_digits)

    def _is_l10n_eg_edi_applicable(self, mode):
        return (
            self.company_id.l10n_eg_edi_api_mode == mode
            and self.country_code == 'EG'
            and self.state == 'posted'
            and self.l10n_eg_edi_submission_state in ['to_send', 'rejected']
        )

    def _generate_l10n_eg_edi_json(self, is_demo=False):
        self.ensure_one()
        AccountTax = self.env['account.tax']
        base_amls = self.line_ids.filtered(lambda x: x.display_type == 'product')
        base_lines = [self._prepare_product_base_line_for_taxes_computation(x) for x in base_amls]
        tax_amls = self.line_ids.filtered('tax_repartition_line_id')
        tax_lines = [self._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id, tax_lines=tax_lines)

        # Tax amounts per line.

        def grouping_function_base_line(base_line, tax_data):
            if not tax_data:
                return None
            tax = tax_data['tax']
            code_split = tax.l10n_eg_eta_code.split('_')
            return {
                'rate': abs(tax.amount) if tax.amount_type != 'fixed' else 0,
                'tax_type': code_split[0].upper(),
                'sub_type': code_split[1].upper(),
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function_base_line)
        invoice_line_data, totals = self._l10n_eg_eta_prepare_invoice_lines_data(base_lines_aggregated_values)

        # Tax amounts for the whole document.

        def grouping_function_global(base_line, tax_data):
            if not tax_data:
                return None
            tax = tax_data['tax']
            code_split = tax.l10n_eg_eta_code.split('_')
            return {
                'tax_type': code_split[0].upper(),
            }

        def grouping_function_total_amount(base_line, tax_data):
            return True if tax_data else None

        base_lines_aggregated_values_total_amount = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function_total_amount)
        values_per_grouping_key_total_amount = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values_total_amount)

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function_global)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)

        date_string = self.invoice_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        eta_invoice = {
            'issuer': self._l10n_eg_eta_prepare_address_data(self.journal_id.l10n_eg_branch_id, issuer=True),
            'receiver': self._l10n_eg_eta_prepare_address_data(self.partner_id),
            'documentType': 'i' if self.move_type == 'out_invoice' else 'c' if self.move_type == 'out_refund' else 'd' if self.move_type == 'in_refund' else '',
            'documentTypeVersion': '1.0',
            'dateTimeIssued': date_string,
            'taxpayerActivityCode': self.journal_id.l10n_eg_activity_type_id.code,
            'internalID': self.name,
            'invoiceLines': invoice_line_data,
            'taxTotals': [
                {
                    'taxType': grouping_key['tax_type'],
                    'amount': self._l10n_eg_edi_round(abs(tax_values['tax_amount'])),
                }
                for grouping_key, tax_values in values_per_grouping_key.items()
                if grouping_key
            ],
            'totalDiscountAmount': self._l10n_eg_edi_round(totals['discount_total']),
            'totalSalesAmount': self._l10n_eg_edi_round(totals['total_price_subtotal_before_discount']),
            'netAmount': self._l10n_eg_edi_round(sum(x['base_amount'] for x in values_per_grouping_key_total_amount.values())),
            'totalAmount': self._l10n_eg_edi_round(sum(x['base_amount'] + x['tax_amount'] for x in values_per_grouping_key_total_amount.values())),
            'extraDiscountAmount': 0.0,
            'totalItemsDiscountAmount': 0.0,
        }
        if self.ref:
            eta_invoice['purchaseOrderReference'] = self.ref
        if self.invoice_origin:
            eta_invoice['salesOrderReference'] = self.invoice_origin
        # If the invoice is being generated in test mode, append a dummy signature to it
        if is_demo:
            eta_invoice['signatures'] = [{'i': 'i'}]
        return eta_invoice

    def _l10n_eg_eta_prepare_invoice_lines_data(self, base_lines_aggregated_values):
        lines = []
        totals = {
            'discount_total': 0.0,
            'total_price_subtotal_before_discount': 0.0,
        }
        for base_line, aggregated_values in base_lines_aggregated_values:
            line = base_line['record']
            tax_details = base_line['tax_details']
            has_full_line_discount = float_compare(line.discount, 100.00, precision_digits=2)
            price_unit = (
                (line.quantity and has_full_line_discount)
                and self._l10n_eg_edi_round(abs((line.balance / line.quantity) / (1 - (line.discount / 100.0))))
                or line.price_unit
            )
            price_subtotal_before_discount = (
                has_full_line_discount
                and self._l10n_eg_edi_round(abs(line.balance / (1 - (line.discount / 100))))
                or self._l10n_eg_edi_round(price_unit * line.quantity)
            )
            discount_amount = self._l10n_eg_edi_round(price_subtotal_before_discount - abs(line.balance))
            item_code = line.product_id.l10n_eg_eta_code or line.product_id.barcode or ''
            lines.append({
                'description': line.name,
                'itemType': item_code.startswith('EG') and 'EGS' or 'GS1',
                'itemCode': item_code,
                'unitType': line.product_uom_id.l10n_eg_unit_code_id.code,
                'quantity': line.quantity,
                'internalCode': line.product_id.default_code or '',
                'valueDifference': 0.0,
                'totalTaxableFees': 0.0,
                'itemsDiscount': 0.0,
                'unitValue': {
                    'currencySold': self.currency_id.name,
                    'amountEGP': price_unit,
                },
                'discount': {
                    'rate': line.discount,
                    'amount': discount_amount,
                },
                'taxableItems': [
                    {
                        'taxType': grouping_key['tax_type'],
                        'amount': self._l10n_eg_edi_round(abs(tax_values['tax_amount'])),
                        'subType': grouping_key['sub_type'],
                        'rate': grouping_key['rate'],
                    }
                    for grouping_key, tax_values in aggregated_values.items()
                    if grouping_key
                ],
                'salesTotal': price_subtotal_before_discount,
                'netTotal': self._l10n_eg_edi_round(tax_details['total_excluded'] + tax_details['delta_total_excluded']),
                'total': self._l10n_eg_edi_round(tax_details['total_included']),
            })
            totals['discount_total'] += discount_amount
            totals['total_price_subtotal_before_discount'] += price_subtotal_before_discount
            if self.currency_id != self.env.ref('base.EGP'):
                lines[-1]['unitValue']['currencyExchangeRate'] = self._l10n_eg_edi_round(self._l10n_eg_edi_exchange_currency_rate())
                lines[-1]['unitValue']['amountSold'] = line.price_unit
        return lines, totals

    def _l10n_eg_eta_prepare_address_data(self, partner, issuer=False):
        address = {
            'address': {
                'country': partner.country_id.code,
                'governate': partner.state_id.name or '',
                'regionCity': partner.city or '',
                'street': ' '.join(s for s in [partner.street, partner.street2] if s),
                'buildingNumber': partner.l10n_eg_building_no or '',
                'postalCode': partner.zip or '',
            },
            'name': partner.name,
        }
        if issuer:
            address['address']['branchID'] = self.journal_id.l10n_eg_branch_identifier or ''
        individual_type = self._l10n_eg_get_partner_tax_type(partner, issuer)
        address['type'] = individual_type or ''
        if individual_type != 'P':
            address['id'] = partner.vat or ''
        return address

    def _l10n_eg_get_partner_tax_type(self, partner_id, issuer=False):
        if issuer:
            return 'B'
        if partner_id.commercial_partner_id.country_code == 'EG':
            return 'B' if partner_id.commercial_partner_id.is_company else 'P'
        return 'F'

    def _l10n_eg_edi_send_invoices_in_batch(self, notify=False):
        """
        ETA Supports sending multiple invoices to it and they send back a response containing results
        for all the invoices sent to it.
        So we send multiple invoices to ETA in a fix batch size and process their responses.
        """
        for i in range(0, len(self.ids), ETA_INVOICE_SENDING_BATCH_SIZE):
            batch = self[i:i + ETA_INVOICE_SENDING_BATCH_SIZE]
            if error := batch._l10n_eg_eta_send_invoice(notify=notify):
                return error

    def _l10n_eg_eta_send_invoice(self, notify=False):
        access_data = self._l10n_eg_eta_get_access_token()
        if access_data.get('error'):
            return access_data
        request_url = '/api/v1.0/documentsubmissions'
        request_invoices = {
            inv.id: json.loads(inv.l10n_eg_eta_json_doc_file.content)['request']
            for inv in self
        }
        body = json.dumps(
            {'documents': list(request_invoices.values())},
            ensure_ascii=False,
            indent=4
        ).encode('utf-8')
        headers = self._l10n_eg_edi_prepare_headers(access_data.get('access_token'))
        _response, data = self._l10n_eg_edi_eta_request(
            url=request_url,
            method='POST',
            body=body,
            headers=headers,
        )
        if data.get('error'):
            return data
        submission_id = data.get('submissionId')
        accepted_docs = data.get('acceptedDocuments', [])
        rejected_docs = data.get('rejectedDocuments', [])
        for invoice in self:
            if accepted_inv := next((doc for doc in accepted_docs if doc.get('internalId') == invoice.name), None):
                invoice._l10n_eg_log_and_update_attachment(accepted_inv, submission_id, success=True, notify=notify)
            elif rejected_inv := next((doc for doc in rejected_docs if doc.get('internalId') == invoice.name), None):
                invoice._l10n_eg_log_and_update_attachment(rejected_inv, submission_id, success=False, notify=notify)

    def _l10n_eg_log_and_update_attachment(self, response, submission_id, success, notify=False):
        """Log the response from ETA and update the attachment with the submission details."""
        attachment_name = f'eta_request_response_json_{self.name}'
        submission_values = {
            'move_id': self.id,
            'eta_submission_id': submission_id,
        }
        if not success:
            response_message = self.env._("""
                    Error: Invoice rejected by ETA\n
                    [%(code)s] %(message)s %(details)s
                """,
                code=response['error']['code'],
                message=response['error']['message'],
                details=response['error'].get('details', ''),
            )
            submission_values.update({
                'state': 'rejected',
                'message': response_message,
            })
            self.l10n_eg_edi_submission_state = 'rejected'
            self.l10n_eg_is_signed = False
        else:
            submission_values.update({
                'state': 'test' if self.company_id.l10n_eg_edi_api_mode != 'production' else 'accepted',
                'message': self.env._("Success: Invoice accepted by ETA."),
                'eta_document_uuid': response.get('uuid'),
                'eta_document_longid': response.get('longId'),
                'eta_json_filename': attachment_name,
            })
            self.l10n_eg_edi_submission_state = 'test' if self.company_id.l10n_eg_edi_api_mode != 'production' else 'accepted'

        invoice_json = json.loads(self.l10n_eg_eta_json_doc_file.content)
        invoice_json['response'] = response
        self.l10n_eg_eta_json_doc_file = BinaryBytes(json.dumps(invoice_json).encode())
        if success:
            # If the submission is successful, store the JSON in attachments
            self.env['ir.attachment'].create({
                'name': attachment_name,
                'description': 'ETA Request-Response JSON not to be deleted',
                'res_id': self.id,
                'res_model': self._name,
                'raw': json.dumps(dict(request=invoice_json)).encode(),
                'mimetype': 'application/json',
            })
        self.invalidate_recordset(fnames=['l10n_eg_eta_json_doc_file'])
        self.env['l10n_eg_edi.eta.submission'].create([submission_values])
        if notify:
            self.env.user._bus_send('simple_notification', {
                'type': 'success' if success else 'danger',
                'message': self.env._("Document successfully accepted!") if success else self.env._("Document is rejected. Please check it and try again.")
            })

    def _l10n_eg_get_eta_invoice_pdf(self, access_token):
        """This method fetches the PDF Invoice as per the format set by ETA."""
        self.ensure_one()
        headers = self._l10n_eg_edi_prepare_headers(access_token)
        request_url = f'/api/v1.0/documents/{self.l10n_eg_uuid}/pdf'
        response, data = self._l10n_eg_edi_eta_request(
            url=request_url,
            method='GET',
            body=None,
            headers=headers,
            timeout=(20, 40),
        )
        if data.get('error') or not response or not response.ok:
            return False
        pdf_content = response.content
        attachment = self.env['ir.attachment'].create({
            'name': _('ETA_INVOICE_PDF_%s', self.name),
            'res_id': self.id,
            'res_model': self._name,
            'type': 'binary',
            'raw': pdf_content,
            'mimetype': 'application/pdf',
            'description': self.env._("Egyptian Tax authority PDF invoice generated for %s.", self.name),
        })
        self.message_post(
            body=self.env._("PDF Invoice fetched successfully from ETA."),
            attachment_ids=attachment.ids,
        )
        return True

    def _l10n_eg_edi_cancel_invoices(self, cancel_reason, notify=False):
        eg_moves = self.filtered(lambda m: m.country_code == 'EG' and m.l10n_eg_edi_submission_state in ['test', 'accepted'])
        if not eg_moves:
            self.env.user._bus_send('simple_notification', {
                'type': 'warning',
                'message': self.env._("The selected invoices are not yet valid to be cancelled on ETA.")
            })
            return
        for move in eg_moves:
            if move.l10n_eg_edi_api_mode == 'demo':
                move._l10n_eg_edi_log_on_cancel(cancel_reason, notify)
            else:
                move._l10n_eg_edi_cancel_invoice(cancel_reason, notify)

    def _l10n_eg_edi_cancel_invoice(self, cancel_reason, notify=False):
        access_data = self._l10n_eg_eta_get_access_token()
        if error := access_data.get('error'):
            raise UserError(self.env._(
                "Error occured while fetching access token: [%(code)s] %(message)s",
                code=error.get('code'),
                message=error.get('message'),
            ))
        if self.l10n_eg_edi_submission_state == 'cancel':
            raise UserError(self.env._("Cannot cancel an invoice which is already cancelled !"))

        headers = self._l10n_eg_edi_prepare_headers(access_data.get('access_token'))
        body = json.dumps({'status': 'cancelled', 'reason': cancel_reason}).encode()
        request_url = f'/api/v1.0/documents/state/{self.l10n_eg_uuid}/state'
        response, data = self._l10n_eg_edi_eta_request(
            url=request_url,
            method='PUT',
            headers=headers,
            body=body,
        )
        if not data or not response or not response.ok:
            error = data.get('error', {})
            raise UserError(self.env._(
                "Error occured when trying to cancel invoice: [%(code)s] %(message)s",
                code=error.get('code'),
                message=error.get('message')
            ))
        # Create log for document cancellation.
        self._l10n_eg_edi_log_on_cancel(cancel_reason, notify=notify)

    def _l10n_eg_edi_log_on_cancel(self, cancel_reason, notify=False):
        self.env['l10n_eg_edi.eta.submission'].create({
            'move_id': self.id,
            'state': 'cancel',
            'message': self.env._("Document cancelled on ETA."),
        })
        self.l10n_eg_cancel_reason = cancel_reason
        if notify:
            self.env.user._bus_send('simple_notification', {
                'type': 'info',
                'message': self.env._("Document is cancelled.")
            })

    def _l10n_eg_edi_simulate_send_invoices(self, notify=False):
        for move in self:
            einvoice_json = move._generate_l10n_eg_edi_json()
            self.env['ir.attachment'].create({
                'name': _('ETA_INVOICE_DOC_%s', move.name),
                'res_id': move.id,
                'res_model': move._name,
                'res_field': 'l10n_eg_eta_json_doc_file',
                'raw': json.dumps({'request': einvoice_json}).encode(),
                'mimetype': 'application/json',
            })
            move._l10n_eg_log_and_update_attachment(ETA_INVOICE_DUMMY_RESPONSE, ETA_DUMMY_SUBMISSION_ID, success=True, notify=notify)

    # ===================================================
    # EDI API Methods
    # ===================================================

    @api.model
    def _l10n_eg_get_eta_qr_domain(self, is_production=True):
        return is_production and ETA_DOMAINS['invoice.production'] or ETA_DOMAINS['invoice.demo']

    @api.model
    def _l10n_eg_get_eta_api_domain(self, is_demo=False):
        return is_demo and ETA_DOMAINS['demo'] or ETA_DOMAINS['production']

    @api.model
    def _l10n_eg_get_eta_token_domain(self, is_demo=False):
        return is_demo and ETA_DOMAINS['token.demo'] or ETA_DOMAINS['token.production']

    @api.model
    def _l10n_eg_edi_prepare_headers(self, bearer_token):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {bearer_token}',
        }

    def _l10n_eg_edi_eta_request(self, url, method, body, headers, is_access_token_req=False, timeout=20):
        is_demo = self.company_id.l10n_eg_edi_api_mode == 'preproduction'
        api_domain = is_access_token_req and self._l10n_eg_get_eta_token_domain(is_demo) or self._l10n_eg_get_eta_api_domain(is_demo)
        request_url = api_domain + url
        try:
            session = requests.session()
            session.mount("https://", LegacyHTTPAdapter())
            response = session.request(method, request_url, data=body, headers=headers, timeout=timeout)
        except requests.exceptions.MissingSchema:
            return False, self._l10n_eg_parse_error(message=self.env._("Invalid URL schema. Please check the URL and try again."))
        except requests.exceptions.ConnectionError:
            return False, self._l10n_eg_parse_error(message=self.env._("Failed to connect to ETA. Please try again later."))
        except requests.exceptions.Timeout:
            return False, self._l10n_eg_parse_error(message=self.env._("Request to ETA timed out. Please try again later."))

        try:
            response_data = response.json() or {}
        except JSONDecodeError:
            response_data = self._l10n_eg_parse_error(message=self.env._("Failed to load the response data."))
        return response, response_data

    def _l10n_eg_eta_get_access_token(self):
        user = self.company_id.sudo().l10n_eg_client_identifier
        secret = self.company_id.sudo().l10n_eg_client_secret
        request_url = '/connect/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        body = {'grant_type': 'client_credentials', 'client_id': user, 'client_secret': secret}
        _response, data = self._l10n_eg_edi_eta_request(
            url=request_url,
            method='POST',
            body=body,
            headers=headers,
            is_access_token_req=True
        )
        if data.get('error'):
            return data
        return {'access_token': data.get('access_token')}

    @api.model
    def _l10n_eg_parse_error(self, message):
        return {
            'error': {
                'code': '000',
                'message': message,
            },
        }
