from odoo import _, api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_es_edi_verifactu_send_enable = fields.Boolean(
        compute='_compute_l10n_es_edi_verifactu_compute_checkbox',
        store=True,
    )
    l10n_es_edi_verifactu_send_readonly = fields.Boolean(
        compute='_compute_l10n_es_edi_verifactu_compute_checkbox',
        store=True,
    )
    l10n_es_edi_verifactu_send_checkbox = fields.Boolean(
        string="Veri*Factu",
        compute='_compute_l10n_es_edi_verifactu_compute_checkbox',
        store=True,
        readonly=False,
        help="Create a Veri*Factu Document to register or update the record and send it to the AEAT.",
    )
    # TODO: in saas-17.4: replace it with `warnings` field
    l10n_es_edi_verifactu_warnings = fields.Char(
        compute='_compute_l10n_es_edi_verifactu_warnings',
        store=True,
    )

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_es_edi_verifactu_send'] = self.l10n_es_edi_verifactu_send_checkbox
        return values

    @api.depends('move_ids.l10n_es_edi_verifactu_state')
    def _compute_l10n_es_edi_verifactu_compute_checkbox(self):
        for wizard in self:
            any_moves_require_verifactu = any(wizard.move_ids.mapped('l10n_es_edi_verifactu_required'))
            enable = any_moves_require_verifactu or any(move.country_code == 'ES' for move in wizard.move_ids)
            checked_by_default = enable and any_moves_require_verifactu
            readonly = True
            wizard.l10n_es_edi_verifactu_send_enable = enable
            wizard.l10n_es_edi_verifactu_send_readonly = readonly
            wizard.l10n_es_edi_verifactu_send_checkbox = checked_by_default

    @api.depends('l10n_es_edi_verifactu_send_readonly')
    def _compute_l10n_es_edi_verifactu_warnings(self):
        for wizard in self:
            waiting_moves = wizard.move_ids.filtered(lambda m: m.l10n_es_edi_verifactu_document_ids.filtered(lambda rd: not rd.state))
            wizard.l10n_es_edi_verifactu_warnings = _(
                "The following entries will be skipped. They are already waiting to send Veri*Factu records to the AEAT: %s",
                ', '.join(waiting_moves.mapped('name'))
            ) if waiting_moves else False

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        invoices_to_send = self.env['account.move'].browse([
            invoice.id for invoice, invoice_data in invoices_data.items()
            if invoice_data.get('l10n_es_edi_verifactu_send')
        ]).filtered(lambda move: move.l10n_es_edi_verifactu_required)

        created_document = self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(invoices_to_send)

        for invoice in invoices_to_send:
            # The creation of a document is skipped for `invoice` in case there are waiting documents
            document = created_document.get(invoice)
            if document and document.state == 'creating_failed':
                invoices_data[invoice]['error'] = {
                    'error_title': _("The Veri*Factu record XML could not be created for all invoices."),
                    'errors': [_("See the 'Veri*Factu' tab for more information.")],
                }

        if self._can_commit():
            self._cr.commit()
