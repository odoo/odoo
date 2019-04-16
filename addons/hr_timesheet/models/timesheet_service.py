# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TimesheetService(models.Model):
    _name = 'timesheet.service'
    _description = 'Timesheet Service Pack'

    def _selection_res_model(self):
        selection_list = []
        for model_name in self.env.keys():
            if issubclass(type(self.env[model_name]), self.env.registry['timesheet.service.mixin']):
                selection_list.append((model_name, self.env[model_name]._description))
        return selection_list

    name = fields.Char("Name")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False, required=True)
    res_model = fields.Selection(selection='_selection_res_model', string="Related Document Model", copy=False)
