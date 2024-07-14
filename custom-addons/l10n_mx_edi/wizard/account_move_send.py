from odoo import _, api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_mx_edi_enable_cfdi = fields.Boolean(compute='_compute_l10n_mx_edi_enable_cfdi')
    l10n_mx_edi_checkbox_cfdi = fields.Boolean(
        string="CFDI",
        compute='_compute_l10n_mx_edi_checkbox_cfdi',
        store=True,
        readonly=False,
    )
    l10n_mx_edi_warnings = fields.Json(compute='_compute_l10n_mx_edi_warnings')

    @api.model
    def _get_default_l10n_mx_edi_enable_cfdi(self, move):
        return (
            not move.invoice_pdf_report_id \
            and move.l10n_mx_edi_is_cfdi_needed \
            and move.l10n_mx_edi_cfdi_state not in ('sent', 'global_sent')
        )

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_mx_edi_cfdi'] = self.l10n_mx_edi_checkbox_cfdi
        return values

    @api.model
    def _get_wizard_vals_restrict_to(self, only_options):
        # EXTENDS 'account'
        values = super()._get_wizard_vals_restrict_to(only_options)
        return {
            'l10n_mx_edi_checkbox_cfdi': False,
            **values,
        }

    def _l10n_mx_edi_check_invoices(self):
        moves_to_check = self.move_ids.filtered(self._get_default_l10n_mx_edi_enable_cfdi)
        invalid_records = moves_to_check.partner_id.filtered(
            lambda p: not p.country_id
        )
        if invalid_records:
            return {
                "partner_country_missing": {
                    "message": _("The following partner(s) have an RFC but no country configured."),
                    "action_text": _("View Partner(s)"),
                    "action": invalid_records._get_records_action(
                        name=_("Check Country on Partner(s)")
                    ),
                }
            }

        return {}

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_mx_edi_checkbox_cfdi')
    def _compute_l10n_mx_edi_warnings(self):
        for wizard in self:
            if wizard.l10n_mx_edi_checkbox_cfdi:
                wizard.l10n_mx_edi_warnings = wizard._l10n_mx_edi_check_invoices()
            else:
                wizard.l10n_mx_edi_warnings = False

    @api.depends('move_ids')
    def _compute_l10n_mx_edi_enable_cfdi(self):
        for wizard in self:
            wizard.l10n_mx_edi_enable_cfdi = any(wizard._get_default_l10n_mx_edi_enable_cfdi(m) for m in wizard.move_ids)

    @api.depends('l10n_mx_edi_checkbox_cfdi')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    @api.depends('l10n_mx_edi_enable_cfdi')
    def _compute_l10n_mx_edi_checkbox_cfdi(self):
        for wizard in self:
            wizard.l10n_mx_edi_checkbox_cfdi = wizard.l10n_mx_edi_enable_cfdi

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        attachments = super()._get_invoice_extra_attachments(move)
        if move.l10n_mx_edi_cfdi_state == 'sent':
            attachments += move.l10n_mx_edi_cfdi_attachment_id
        return attachments

    def _get_placeholder_mail_attachments_data(self, move):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move)

        if (
            not move.l10n_mx_edi_cfdi_attachment_id \
            and self.l10n_mx_edi_enable_cfdi \
            and self.l10n_mx_edi_checkbox_cfdi
        ):
            filename = move._l10n_mx_edi_get_invoice_cfdi_filename()
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

            if invoice_data.get('l10n_mx_edi_cfdi') and self._get_default_l10n_mx_edi_enable_cfdi(invoice):
                # Sign it.
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

                # Check for success.
                if invoice.l10n_mx_edi_cfdi_state == 'sent':
                    continue

                # Check for error.
                errors = []
                for document in invoice.l10n_mx_edi_invoice_document_ids:
                    if document.state == 'invoice_sent_failed':
                        errors.append(document.message)
                        break

                invoice_data['error'] = {
                    'error_title': _("Error when sending the CFDI to the PAC:"),
                    'errors': errors,
                }

                if self._can_commit():
                    self._cr.commit()
