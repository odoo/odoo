from odoo import api, models, _
from odoo.exceptions import UserError


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.ondelete(at_uninstall=False)
    def _unlink_sequence(self):
        for seq in self:
            pos = self.env['pos.session'].search(domain=[('login_number_seq_id', '=', seq.id)], limit=1)
            if not self._context.get('delete_from_unlink_session') and pos and pos.state != 'closed':
                raise UserError(_('You cannot delete a sequence that is currently in use by a POS session.'))
