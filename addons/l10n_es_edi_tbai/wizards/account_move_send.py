from odoo import _, api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_es_tbai_show_checkbox = fields.Boolean(compute='_compute_l10n_es_tbai_show_checkbox')
    l10n_es_tbai_checkbox_send = fields.Boolean(
        string='TicketBAI',
        compute='_compute_l10n_es_tbai_checkbox_send',
        store=True,
        readonly=False,
        help="Send the e-invoice to the Basque Government.",
    )

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_es_tbai_checkbox_send'] = self.l10n_es_tbai_checkbox_send
        return values

    @api.model
    def _get_wizard_vals_restrict_to(self, only_options):
        # EXTENDS 'account'
        values = super()._get_wizard_vals_restrict_to(only_options)
        return {
            'l10n_es_tbai_checkbox_send': False,
            **values,
        }

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_l10n_es_tbai_show_checkbox(self):
        for wizard in self:
            wizard.l10n_es_tbai_show_checkbox = any(move.l10n_es_tbai_is_required for move in wizard.move_ids)

    @api.depends('l10n_es_tbai_show_checkbox')
    def _compute_l10n_es_tbai_checkbox_send(self):
        for wizard in self:
            wizard.l10n_es_tbai_checkbox_send = wizard.l10n_es_tbai_show_checkbox and any(move.l10n_es_tbai_state == 'to_send' for move in wizard.move_ids)

    @api.depends('l10n_es_tbai_checkbox_send')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_es_tbai_post_attachment_id

    def _get_placeholder_mail_attachments_data(self, move):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move)

        if (
            not move.l10n_es_tbai_post_attachment_id
            and self.l10n_es_tbai_show_checkbox
            and self.l10n_es_tbai_checkbox_send
        ):
            filename = move._l10n_es_tbai_get_attachment_name()
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/xml',
                'placeholder': True,
            })

        return results

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():

            if invoice_data.get('l10n_es_tbai_checkbox_send'):
                error = invoice._l10n_es_tbai_post()

                if error:
                    invoice_data['error'] = {
                        'error_title': _("Error when sending the invoice to TicketBAI:"),
                        'errors': [error],
                    }

                if self._can_commit():
                    self._cr.commit()
