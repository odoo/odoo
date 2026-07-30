from odoo import fields, models


class L10nCrFeMrMotivoWizard(models.TransientModel):
    _name = 'l10n_cr.fe.mr.motivo.wizard'
    _description = "Motivo del Mensaje Receptor (aceptación parcial / rechazo)"

    move_id = fields.Many2one('account.move', required=True, readonly=True)
    decision = fields.Selection([
        ('aceptado_parcial', "Aceptado parcialmente"),
        ('rechazado', "Rechazado"),
    ], required=True, readonly=True)
    motivo = fields.Char(string="Motivo", required=True)

    def action_confirmar(self):
        self.ensure_one()
        self.move_id.l10n_cr_fe_mr_motivo = self.motivo
        if self.decision == 'aceptado_parcial':
            self.move_id.action_l10n_cr_fe_aceptar_parcial()
        else:
            self.move_id.action_l10n_cr_fe_rechazar()
        return {'type': 'ir.actions.act_window_close'}
