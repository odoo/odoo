from odoo import fields, models


class MrpWorkcenterUnblock(models.TransientModel):
    _name = 'mrp.workcenter.unblock'
    _description = 'Unblock work centers'

    workcenter_ids = fields.Many2many('mrp.workcenter', required=True)
    message = fields.Char(required=True)

    def action_unblock(self):
        blocked = self.workcenter_ids.filtered(lambda wc: wc.working_state == 'blocked')
        for wc in blocked:
            wc.unblock()
        if blocked:
            wc_names = ', '.join(blocked.mapped('name'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': self.env._('Work Center %s has been unblocked', wc_names) if len(blocked) == 1
                            else self.env._('Work Centers %s have been unblocked', wc_names),
                    'type': 'success',
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
