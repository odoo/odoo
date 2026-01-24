import logging
import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import _mer_api_send, MojEracunServiceError

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _check_move_constrains(self, moves):
        # HR-BR-37: Invoice must contain HR-BT-4: Operator code in accordance with the Fiscalization Act.
        if any((move.country_code == 'HR' and not move.l10n_hr_operator_name) for move in moves):
            raise UserError(self.env._("Operator label is required for sending invoices in Croatia."))
        # HR-BR-9: Invoice must contain HR-BT-5: Operator OIB in accordance with the Fiscalization Act.
        if any((move.country_code == 'HR' and not move.l10n_hr_operator_oib) for move in moves):
            raise UserError(self.env._("Operator OIB is required for sending invoices in Croatia."))
        # HR-BR-25: ensure KPD is provided for every business line except for advance (P4)
        if any((move.country_code == 'HR' and move.l10n_hr_process_type != 'P4' and
                any(line.display_type == 'product' and not line.l10n_hr_kpd_category_id for line in move.line_ids)) for move in moves):
            raise UserError(self.env._('KPD categories must be defined on every invoice line for any Business Process Type other than P4.'))
        if any((move.country_code == 'HR' and move.l10n_hr_process_type == 'P99' and not move.l10n_hr_customer_defined_process_name) for move in moves):
            raise UserError(self.env._('Name of custom business process is required for Business Process Type P99.'))
        if any((move.country_code == 'HR' and
                len({line.tax_ids.tax_exigibility for line in move.line_ids if line.display_type == 'product'}) != 1) for move in moves):
            raise ValidationError(self.env._('For Croatia, all VAT taxes on an invoice should either be cash basis or not.'))
        if any(move.country_code == 'HR' and
            any(any((tax.tax_exigibility == 'on_payment' and not tax.invoice_legal_notes) for tax in line.tax_ids
             ) for line in move.line_ids if line.display_type == 'product') for move in moves):
            raise ValidationError(self.env._('For Croatia, Legal Notes should be provided for all cash basis taxes.'))
        super()._check_move_constrains(moves)

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _get_default_invoice_edi_format(self, move, **kwargs) -> str:
        # EXTENDS 'account'
        if 'mojeracun' in kwargs.get('sending_methods', []):
            return 'ubl_hr'
        return super()._get_default_invoice_edi_format(move, **kwargs)

    def _is_applicable_to_company(self, method, company):
        # EXTENDS 'account'
        if method == 'mojeracun':
            return company.l10n_hr_mer_connection_state == 'active' and company.country_code == 'HR'
        return super()._is_applicable_to_company(method, company)

    def _is_applicable_to_move(self, method, move, **move_data):
        # EXTENDS 'account'
        if method == 'mojeracun':
            partner = move.partner_id.commercial_partner_id.with_company(move.company_id)
            invoice_edi_format = move_data.get('invoice_edi_format') or 'ubl_hr'
            return all([
                self._is_applicable_to_company(method, move.company_id),
                partner.vat,    # Alternatively, partner GLN when proper support for that is added
                move._need_ubl_cii_xml(invoice_edi_format)
                or (move.ubl_cii_xml_id and move.l10n_hr_mer_document_status not in {'20', '30', '40'}),
            ])
        return super()._is_applicable_to_move(method, move, **move_data)

    def _hook_if_errors(self, moves_data, allow_raising=True):
        # EXTENDS 'account'
        moves_failed_file_generation = self.env['account.move']
        for move, move_data in moves_data.items():
            if 'mojeracun' in move_data['sending_methods'] and move_data.get('blocking_error'):
                moves_failed_file_generation |= move
        moves_failed_file_generation.l10n_hr_mer_document_status = '50'
        return super()._hook_if_errors(moves_data, allow_raising=allow_raising)

    @api.model
    def _generate_and_send_invoices(self, moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings):
        for move in moves:
            if move.country_code == 'HR' and move.is_sale_document():
                move.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
                    'move_id': move.id,
                    'fiscalization_number': move._get_l10n_hr_fiscalization_number(move.name),
                    'invoice_sending_time': fields.Datetime.now(pytz.timezone('Europe/Zagreb')),
                })
        return super()._generate_and_send_invoices(moves, from_cron=from_cron, allow_raising=allow_raising, allow_fallback_pdf=allow_fallback_pdf, **custom_settings)

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            # MojEracun determines the receiver endpoint entirely from the XML,
            # so there is no need to check for partner endpoint
            if 'mojeracun' not in invoice_data['sending_methods']:
                continue
            if not self._is_applicable_to_move('mojeracun', invoice, **invoice_data):
                raise UserError(self.env._("Failed to send invoice via MojEracun: check configuration."))

            if invoice_data.get('ubl_cii_xml_attachment_values'):
                xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
            elif invoice.ubl_cii_xml_id and invoice.l10n_hr_mer_document_status not in {'20', '30', '40'}:
                xml_file = invoice.ubl_cii_xml_id.raw
            else:
                invoice.l10n_hr_edi_addendum_id.mer_document_status = '50'
                builder = invoice.partner_id.commercial_partner_id._get_edi_builder(invoice_data['invoice_edi_format'])
                invoice_data['error'] = self.env._(
                    "Errors occurred while creating the EDI document (format: %s):",
                    builder._description,
                )
                return
            addendum = invoice.l10n_hr_edi_addendum_id
            try:
                response = _mer_api_send(invoice.company_id, xml_file.decode())
            except MojEracunServiceError as e:
                addendum.mer_document_status = '50'
                invoice_data['error'] = e.message
            else:
                if not response.get('ElectronicId'):
                    addendum.mer_document_status = '50'
                    errors = []
                    for key in response:
                        errors.append(' '.join(response[key].get('Messages', [])))
                    invoice_data['error'] = {'error_title': "Error", 'errors': errors}
                else:
                    addendum.mer_document_eid = response['ElectronicId']
                    addendum.mer_document_status = '20'
                    log_message = self.env._('The document has been sent to MojEracun service provider for processing')
                    invoice._message_log(body=log_message)
            if self._can_commit():
                self.env.cr.commit()
