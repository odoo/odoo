# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def action_open_deliveries(self):
        self.ensure_one()
        return self._get_picking_action('outgoing', _('From WH'))

    def action_open_receipts(self):
        self.ensure_one()
        return self._get_picking_action('incoming', _('To WH'))

    def _get_picking_action(self, picking_type, action_name):
        return {
            'name': action_name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [
                ('picking_type_id.code', '=', picking_type),
                ('project_id', '=', self.id),
            ],
            'context': {
                **({'default_partner_id': self.partner_id.id} if picking_type == 'outgoing' else {}),
                'default_project_id': self.id,
                'restricted_picking_type_code': picking_type,
            },
        }
