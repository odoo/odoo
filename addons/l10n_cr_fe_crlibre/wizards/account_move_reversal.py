from odoo import api, fields, models

from odoo.addons.l10n_cr_fe_crlibre.models.account_move import (
    L10N_CR_FE_CODIGO_REFERENCIA,
    L10N_CR_FE_MOTIVO_CODIGO_MAP,
    L10N_CR_FE_MOTIVO_NC,
)


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_cr_fe_applicable = fields.Boolean(compute='_compute_l10n_cr_fe_applicable')
    l10n_cr_fe_is_admin = fields.Boolean(compute='_compute_l10n_cr_fe_is_admin')
    l10n_cr_fe_motivo = fields.Selection(L10N_CR_FE_MOTIVO_NC, string="Motivo de la nota de crédito")
    l10n_cr_fe_codigo_referencia = fields.Selection(
        L10N_CR_FE_CODIGO_REFERENCIA, string="Código de referencia Hacienda",
        compute='_compute_l10n_cr_fe_codigo_referencia', store=True, readonly=False)

    @api.depends('move_ids')
    def _compute_l10n_cr_fe_applicable(self):
        for wizard in self:
            wizard.l10n_cr_fe_applicable = bool(
                wizard.move_ids and len(wizard.move_ids) == 1
                and wizard.move_ids.move_type == 'out_invoice'
                and wizard.move_ids.l10n_cr_fe_clave)

    def _compute_l10n_cr_fe_is_admin(self):
        is_admin = self.env.user.has_group('l10n_cr_fe_crlibre.group_fe_admin')
        for wizard in self:
            wizard.l10n_cr_fe_is_admin = is_admin

    @api.depends('l10n_cr_fe_motivo')
    def _compute_l10n_cr_fe_codigo_referencia(self):
        for wizard in self:
            wizard.l10n_cr_fe_codigo_referencia = L10N_CR_FE_MOTIVO_CODIGO_MAP.get(wizard.l10n_cr_fe_motivo)

    def _prepare_default_reversal(self, move):
        return {
            **super()._prepare_default_reversal(move),
            'l10n_cr_fe_motivo': self.l10n_cr_fe_motivo,
            'l10n_cr_fe_codigo_referencia': self.l10n_cr_fe_codigo_referencia,
            'l10n_cr_fe_razon': self.reason,
        }
