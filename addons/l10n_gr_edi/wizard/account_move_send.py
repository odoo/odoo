from odoo import api, fields, models, _


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_gr_edi_send_enable = fields.Boolean(compute='_compute_l10n_gr_edi_send_enable')
    l10n_gr_edi_send_readonly = fields.Boolean(compute='_compute_l10n_gr_edi_send_readonly')
    l10n_gr_edi_send_checkbox = fields.Boolean(
        string='Send to MyDATA',
        compute='_compute_l10n_gr_edi_send_checkbox', store=True, readonly=False,
        help='Send invoice classification data XML to the Greece Government via the MyDATA platform')
    l10n_gr_edi_warnings = fields.Json(compute='_compute_l10n_gr_edi_warnings')  # To be removed in master

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_gr_edi_send'] = self.l10n_gr_edi_send_checkbox
        return values

    @api.depends('move_ids.l10n_gr_edi_state', 'enable_ubl_cii_xml')
    def _compute_l10n_gr_edi_send_enable(self):
        for wizard in self:
            wizard.l10n_gr_edi_send_enable = any(move.l10n_gr_edi_enable_send_invoices for move in wizard.move_ids)

    @api.depends('l10n_gr_edi_send_enable', 'move_ids.l10n_gr_edi_warnings', 'move_ids.l10n_gr_edi_enable_send_invoices')
    def _compute_l10n_gr_edi_send_readonly(self):
        for wizard in self:
            wizard.l10n_gr_edi_send_readonly = not wizard.l10n_gr_edi_send_enable or any(
                move.l10n_gr_edi_warnings or
                not move.l10n_gr_edi_enable_send_invoices
                for move in wizard.move_ids
            )

    @api.depends('l10n_gr_edi_send_readonly')
    def _compute_l10n_gr_edi_send_checkbox(self):
        for wizard in self:
            wizard.l10n_gr_edi_send_checkbox = not wizard.l10n_gr_edi_send_readonly

    @api.depends(
        'l10n_gr_edi_send_enable',
        'l10n_gr_edi_send_readonly',
        'move_ids.l10n_gr_edi_warnings',
        'move_ids.l10n_gr_edi_enable_send_invoices',
    )
    def _compute_l10n_gr_edi_warnings(self):
        """ TODO in master (saas-17.4): merge it with `warnings` field using `_compute_warnings`. """
        for wizard in self:
            gr_warnings = {}
            if wizard.l10n_gr_edi_send_enable and wizard.l10n_gr_edi_send_readonly:
                if any(move.l10n_gr_edi_state == 'move_sent' for move in wizard.move_ids):
                    gr_warnings['l10n_gr_edi_warning_already_sent'] = {
                        'message': _("Some of the selected move(s) have been sent to MyDATA. Please unselect them before sending.")
                    }
                elif len(wizard.move_ids) == 1:  # on a single invoice wizard, display all the MyDATA warnings.
                    if move_warnings := wizard.move_ids.l10n_gr_edi_warnings:
                        gr_warnings = move_warnings
                    elif not wizard.move_ids.l10n_gr_edi_enable_send_invoices:
                        gr_warnings['l10n_gr_edi_warning_not_ready_invoice'] = {
                            'message': _("The selected invoice are not ready to be sent to MyDATA."),
                        }
                else:  # on multi-invoice wizard, only display the problematic move(s) list warning.
                    warning_moves = wizard.move_ids.filtered(lambda m: m.l10n_gr_edi_warnings or not m.l10n_gr_edi_enable_send_invoices)
                    gr_warnings['l10n_gr_edi_warning_some_invoice'] = {
                        'message': _("The following invoice(s) are not ready to be sent to MyDATA."),
                        'action_text': _("View Invoice(s)"),
                        'action': warning_moves._get_records_action(name=_("Check invoice(s) not ready for MyDATA.")),
                    }
            wizard.l10n_gr_edi_warnings = gr_warnings

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        invoices = self.env['account.move']

        for invoice, invoice_data in invoices_data.items():
            if invoice_data.get('l10n_gr_edi_send') and invoice.l10n_gr_edi_state != 'move_sent':
                invoices |= invoice

        # send multiple invoice at once (if available) in one batch
        if invoices:
            invoices.l10n_gr_edi_try_send_invoices()

        for invoice, invoice_data in invoices_data.items():
            if invoice in invoices and invoice.l10n_gr_edi_state == 'move_error':
                invoice_data['error'] = {
                    'error_title': _("Error when sending invoice to MyDATA"),
                    'errors': invoice.l10n_gr_edi_document_ids.sorted()[0].message.split('\n'),
                }
