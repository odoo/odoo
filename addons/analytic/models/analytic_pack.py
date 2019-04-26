# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AnalyticPack(models.Model):
    _name = 'analytic.pack'
    _description = 'Analytic Pack'

    def _selection_res_model(self):
        selection_list = []
        for model_name in self.env.keys():
            if issubclass(type(self.env[model_name]), self.env.registry['analytic.pack.mixin']):
                selection_list.append((model_name, self.env[model_name]._description))
        return selection_list

    name = fields.Char("Name")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False, required=True)
    res_model = fields.Selection(selection='_selection_res_model', string="Related Document Model", copy=False)
    analytic_line_ids = fields.One2many('account.analytic.line', 'analytic_pack_id', string="Analytic Lines")

    @api.multi
    def name_get(self):
        result = []
        for pack in self:
            result.append((pack.id, "%s (%d)" % (pack.name, pack.res_model)))
        return result
