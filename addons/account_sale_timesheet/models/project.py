# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _lt

class Project(models.Model):
    _inherit = 'project.project'

    invoice_count = fields.Integer(related='analytic_account_id.invoice_count', groups='account.group_account_readonly')

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        if self.user_has_groups('account.group_account_readonly'):
            buttons.append({
                'icon': 'pencil-square-o',
                'text': _lt('Invoices'),
                'number': self.invoice_count,
                'action_type': 'object',
                'action': 'action_open_project_invoices',
                'show': bool(self.analytic_account_id) and self.invoice_count > 0,
                'sequence': 11,
            })
        return buttons
