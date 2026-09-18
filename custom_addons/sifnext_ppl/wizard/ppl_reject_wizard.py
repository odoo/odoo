from odoo import _, api, fields, models


class PplRejectWizard(models.TransientModel):
    _name = 'sifnext.ppl.reject.wizard'
    _description = 'Reject PPL Wizard'

    ppl_id = fields.Many2one(
        'sifnext.ppl',
        string='PPL Document',
        required=True,
    )
    reason = fields.Text(
        string='Catatan Revisi',
        required=True,
        help='Berikan catatan revisi mengapa PPL ini dikembalikan. Status PPL akan menjadi Draft.',
    )

    def action_confirm_reject(self):
        self.ensure_one()
        self.ppl_id.action_reject(self.reason)
        return {'type': 'ir.actions.act_window_close'}
