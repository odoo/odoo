from odoo import api, models, _
from odoo.exceptions import UserError


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.ondelete(at_uninstall=False)
    def _unlink_sequence(self):
        sessions = self.env['pos.session'].search(domain=['|', ('login_number_seq_id', 'in', self.ids), ('order_seq_id', 'in', self.ids)])
        acive_sessions = sessions.filtered(lambda s: s.state != 'closed')
        if acive_sessions:
            raise UserError(_(
                "You cannot delete a sequence used in an active session: %s",
                acive_sessions.login_number_seq_id.mapped('name')
            ))
