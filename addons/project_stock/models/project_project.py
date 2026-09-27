# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.fields import Domain


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def action_open_deliveries(self):
        self.ensure_one()
        return self._get_picking_action(_('From WH'), 'outgoing')

    def action_open_receipts(self):
        self.ensure_one()
        return self._get_picking_action(_('To WH'), 'incoming')

    def action_open_all_pickings(self):
        self.ensure_one()
        return self._get_picking_action(_('Stock Moves'))

    def _get_picking_action(self, action_name, picking_type=None):
        domain = Domain('project_id', '=', self.id)
        context = {'default_project_id': self.id}
        if picking_type:
            domain &= Domain('picking_type_id.code', '=', picking_type)
            context['restricted_picking_type_code'] = picking_type
            if picking_type == 'outgoing':
                context['default_partner_id'] = self.partner_id.id
        view_mode = "list,kanban,form,calendar"
        if picking_type != 'outgoing':
            view_mode += ",activity"
        return {
            'name': action_name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': view_mode,
            'domain': domain,
            'context': context,
            'help': self.env['ir.ui.view']._render_template(
                'stock.help_message_template', {
                    'picking_type_code': picking_type,
                }
            ),
        }
