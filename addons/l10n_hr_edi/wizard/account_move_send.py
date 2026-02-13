import logging
import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import _mer_api_send, MojEracunServiceError

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_hr_enable_mer = fields.Boolean(compute='_compute_l10n_hr_enable_mer')

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['send_mojeracun'] = self.l10n_hr_enable_mer and self.checkbox_ubl_cii_xml and self.checkbox_ubl_cii_label == 'CIUS HR'
        return values

    def _compute_l10n_hr_enable_mer(self):
        for wizard in self:
            wizard.l10n_hr_enable_mer = wizard.company_id.l10n_hr_mer_connection_state == 'active' and (not any(
                    move.partner_id.country_code != 'HR' or move.company_id.country_code != 'HR' for move in wizard.move_ids
                ))

    def _check_move_constrains(self, moves):
        # HR-BR-37: Invoice must contain HR-BT-4: Operator code in accordance with the Fiscalization Act.
        if any((move.country_code == 'HR' and not move.l10n_hr_operator_name) for move in moves):
            raise UserError(_("Operator label is required for sending invoices in Croatia."))
        # HR-BR-9: Invoice must contain HR-BT-5: Operator OIB in accordance with the Fiscalization Act.
        if any((move.country_code == 'HR' and not move.l10n_hr_operator_oib) for move in moves):
            raise UserError(_("Operator OIB is required for sending invoices in Croatia."))
        # HR-BR-25: ensure KPD is provided for every business line except for advance (P4)
        if any((move.country_code == 'HR' and move.l10n_hr_process_type != 'P4' and
                any(line.display_type == 'product' and not line.l10n_hr_kpd_category_id for line in move.line_ids)) for move in moves):
            raise UserError(_('KPD categories must be defined on every invoice line for any Business Process Type other than P4.'))
        if any((move.country_code == 'HR' and move.l10n_hr_process_type == 'P99' and not move.l10n_hr_customer_defined_process_name) for move in moves):
            raise UserError(_('Name of custom business process is required for Business Process Type P99.'))
        if any((move.country_code == 'HR' and
                len({line.tax_ids.tax_exigibility for line in move.line_ids if line.display_type == 'product'}) != 1) for move in moves):
            raise ValidationError(_('For Croatia, all VAT taxes on an invoice should either be cash basis or not.'))
        if any(move.country_code == 'HR' and
            any(any((tax.tax_exigibility == 'on_payment' and not tax.invoice_legal_notes) for tax in line.tax_ids
             ) for line in move.line_ids if line.display_type == 'product') for move in moves):
            raise ValidationError(_('For Croatia, Legal Notes should be provided for all cash basis taxes.'))

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
            return all([
                self._is_applicable_to_company(method, move.company_id),
                partner.vat,    # Alternatively, partner GLN when proper support for that is added
                move._need_ubl_cii_xml()
                or (move.ubl_cii_xml_id and move.l10n_hr_mer_document_status not in {'20', '30', '40'}),
            ])
        return super()._is_applicable_to_move(method, move, **move_data)

    def _hook_if_errors(self, moves_data, from_cron=False, allow_fallback_pdf=False):
        # EXTENDS 'account'
        moves_failed_file_generation = self.env['account.move']
        for move, move_data in moves_data.items():
            if move_data.get('send_mojeracun') and move_data.get('blocking_error'):
                moves_failed_file_generation |= move
        moves_failed_file_generation.l10n_hr_mer_document_status = '50'
        return super()._hook_if_errors(moves_data, from_cron=from_cron, allow_fallback_pdf=allow_fallback_pdf)

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        if invoice.country_code == 'HR' and invoice.is_sale_document():
            invoice.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
                'move_id': invoice.id,
                'fiscalization_number': invoice._get_l10n_hr_fiscalization_number(invoice.name),
                'invoice_sending_time': fields.Datetime.now(pytz.timezone('Europe/Zagreb')),
            })
            self._check_move_constrains(invoice)
        return super()._hook_invoice_document_before_pdf_report_render(invoice=invoice, invoice_data=invoice_data)

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            # MojEracun determines the receiver endpoint entirely from the XML,
            # so there is no need to check for partner endpoint
            if not invoice_data.get('send_mojeracun'):
                continue
            if not self._is_applicable_to_move('mojeracun', invoice, **invoice_data):
                raise UserError(_("Failed to send invoice via MojEracun: check configuration."))

            if invoice_data.get('ubl_cii_xml_attachment_values'):
                xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
            elif invoice.ubl_cii_xml_id and invoice.l10n_hr_mer_document_status not in {'20', '30', '40'}:
                xml_file = invoice.ubl_cii_xml_id.raw
            else:
                invoice.l10n_hr_edi_addendum_id.mer_document_status = '50'
                builder = invoice.partner_id.commercial_partner_id._get_edi_builder(invoice_data['invoice_edi_format'])
                invoice_data['error'] = _(
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
                        errors.append(response[key].get('Messages'))
                    invoice_data['error'] = errors
                else:
                    addendum.mer_document_eid = response['ElectronicId']
                    addendum.mer_document_status = '20'
                    log_message = _('The document has been sent to MojEracun service provider for processing')
                    invoice._message_log(body=log_message)
            if self._can_commit():
                self.env.cr.commit()
