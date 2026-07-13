from odoo import api, models, fields


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_sa_edi_enable_zatca = fields.Boolean(compute='_compute_l10n_sa_edi_enable_zatca', string="ZATCA")

    @api.depends('move_ids')
    def _compute_l10n_sa_edi_enable_zatca(self):
        # After sending the invoice to ZATCA it will be false
        for wizard in self:
            wizard.l10n_sa_edi_enable_zatca = any(wizard._get_default_l10n_sa_edi_enable_zatca(m) for m in wizard.move_ids)

    @api.model
    def _is_sa_edi_applicable(self, move):
        zatca_document = move.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'sa_zatca' and d.state == 'to_send')
        return move.country_code == 'SA' and move.move_type in ('out_invoice', 'out_refund') and zatca_document and move.state != 'draft'

    @api.model
    def _get_default_l10n_sa_edi_enable_zatca(self, move):
        return not move.invoice_pdf_report_id and self._is_sa_edi_applicable(move)

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_sa_edi_zatca'] = self.l10n_sa_edi_enable_zatca
        return values

    def _get_placeholder_mail_attachments_data(self, move):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move)

        if self._is_sa_edi_applicable(move):
            filename = self.env['account.edi.xml.ubl_21.zatca']._export_invoice_filename(move)
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/xml',
                'placeholder': True,
            })

        return results

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        to_process = self.env['account.move']
        for invoice, invoice_data in invoices_data.items():
            if invoice_data.get('l10n_sa_edi_zatca'):
                to_process |= invoice
        to_process.action_process_edi_web_services()
