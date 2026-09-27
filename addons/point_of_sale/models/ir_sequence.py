from odoo import api, models, _
from odoo.exceptions import UserError


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.ondelete(at_uninstall=False)
    def _unlink_sequence(self):
        configs = self.env['pos.config'].search(domain=[
            '|', '|', '|',
            ('order_seq_id', 'in', self.ids),
            ('order_line_seq_id', 'in', self.ids),
            ('device_seq_id', 'in', self.ids),
            ('order_backend_seq_id', 'in', self.ids)
        ])
        if len(configs):
            raise UserError(_(
                "You cannot delete a sequence used in an active POS config: %s",
                configs.order_seq_id.mapped('name')
            ))
