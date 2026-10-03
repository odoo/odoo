from odoo import api, fields, models


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = 'account.move.send.batch.wizard'

    l10n_fr_pdp_not_in_annuaire_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        compute='_compute_l10n_fr_pdp_not_in_annuaire_partners',
        string='Partners not in annuaire',
    )
    l10n_fr_pdp_force_send_einvoicing = fields.Boolean(
        string='Force French E-Invoicing',
        help='Send invoices to the DGFiP via your Approved Platform even when buyers '
             'are not registered in the annuaire yet.',
    )

    @api.depends('move_ids')
    def _compute_l10n_fr_pdp_not_in_annuaire_partners(self):
        for wizard in self:
            partners = self.env['res.partner']
            for move in wizard.move_ids:
                partner = move.commercial_partner_id.with_company(move.company_id)
                if partner._l10n_fr_pdp_is_not_in_annuaire():
                    partners |= partner
            wizard.l10n_fr_pdp_not_in_annuaire_partner_ids = partners

    @api.depends('l10n_fr_pdp_force_send_einvoicing', 'move_ids')
    def _compute_summary_data(self):
        no_force = self.filtered(lambda wizard: not wizard.l10n_fr_pdp_force_send_einvoicing)
        with_force = self - no_force
        if no_force:
            super(AccountMoveSendBatchWizard, no_force)._compute_summary_data()
        if with_force:
            super(
                AccountMoveSendBatchWizard,
                with_force.with_context(l10n_fr_pdp_force_send_einvoicing=True),
            )._compute_summary_data()

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False):
        self.ensure_one()
        force_send = self.l10n_fr_pdp_force_send_einvoicing
        if force_send:
            self = self.with_context(l10n_fr_pdp_force_send_einvoicing=True)
        res = super().action_send_and_print(
            force_synchronous=force_synchronous,
            allow_fallback_pdf=allow_fallback_pdf,
        )
        if force_send and not force_synchronous:
            for move in self.move_ids.filtered('sending_data'):
                move.sending_data = {
                    **move.sending_data,
                    'l10n_fr_pdp_force_send_einvoicing': True,
                }
        return res
