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

    def _l10n_es_edi_verifactu_get_move_info(self):
        # EXTENDS 'account'
        self.ensure_one()
        # We do not support sending a registration for already registered move or in case we are waiting to send a document already
        verifactu_moves = self.move_ids.filtered(lambda move: move.l10n_es_edi_verifactu_required)
        waiting_moves = verifactu_moves.filtered(lambda m: m.l10n_es_edi_verifactu_document_ids._filter_waiting())
        registered_moves = verifactu_moves.filtered(
            lambda m: m.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted')
        )
        return {
            'verifactu_moves': verifactu_moves,
            'waiting_moves': waiting_moves,
            'registered_moves': registered_moves,
            'moves_to_send': verifactu_moves - waiting_moves - registered_moves,
        }

    @api.depends('move_ids.l10n_es_edi_verifactu_required', 'move_ids.l10n_es_edi_verifactu_state')
    def _compute_l10n_es_edi_verifactu_compute_checkbox(self):
        for wizard in self:
            move_info = wizard._l10n_es_edi_verifactu_get_move_info()
            enable = move_info['verifactu_moves']
            checked_by_default = move_info['moves_to_send']
            wizard.l10n_es_edi_verifactu_send_enable = enable
            wizard.l10n_es_edi_verifactu_send_checkbox = checked_by_default
            wizard.l10n_es_edi_verifactu_send_readonly = not enable or not move_info['moves_to_send']

    @api.depends('l10n_es_edi_verifactu_send_readonly')
    def _compute_l10n_es_edi_verifactu_warnings(self):
        for wizard in self:
            warnings = []
            move_info = wizard._l10n_es_edi_verifactu_get_move_info()
            if move_info['waiting_moves']:
                warnings.append(_(
                    "The following entries will be skipped. They are already waiting to send Veri*Factu records to the AEAT: %s",
                    ', '.join(move_info['waiting_moves'].mapped('name'))
                ))
            if move_info['registered_moves']:
                warnings.append(_(
                    "The following entries will be skipped. They are already registered with the AEAT: %s",
                    ', '.join(move_info['registered_moves'].mapped('name'))
                ))
            wizard.l10n_es_edi_verifactu_warnings = '\n'.join(warnings) if warnings else False

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        invoices_to_send = self.env['account.move'].browse([
            invoice.id for invoice, invoice_data in invoices_data.items()
            if invoice_data.get('l10n_es_edi_verifactu_send')
        ]).filtered(lambda move: move.l10n_es_edi_verifactu_required)

        created_document = invoices_to_send._l10n_es_edi_verifactu_mark_for_next_batch()

        for invoice in invoices_to_send:
            if not created_document[invoice].chain_index:
                invoices_data[invoice]['error'] = {
                    'error_title': _("The Veri*Factu document could not be created for all invoices."),
                    'errors': [_("See the 'Veri*Factu' tab for more information.")],
                }

        if created_document and self._can_commit():
            self._cr.commit()
