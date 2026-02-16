from ast import literal_eval

from odoo import models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def action_open_analytic_items(self):
        action = self.env['ir.actions.act_window']._for_xml_id('analytic.account_analytic_line_action_entries')
        action['domain'] = [('account_id', '=', self.account_id.id)]
        context = literal_eval(action['context'])
        action['context'] = {
            **context,
            'create': self.env.context.get('from_embedded_action', False),
            'default_account_id': self.account_id.id,
        }
        return action
