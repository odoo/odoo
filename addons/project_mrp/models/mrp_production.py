# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    task_id = fields.Many2one('project.task', string='Task', readonly=True)

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        analytic_account = self.env['account.analytic.account']
        if self._context.get('task_id'):
            task = self.env['project.task'].browse(self._context['task_id'])
            analytic_account = task.analytic_account_id or task.project_id.analytic_account_id
        if analytic_account and analytic_account.active:
            for line in self:
                line.analytic_distribution = {analytic_account.id: 100}

    @api.model_create_multi
    def create(self, vals_list):
        mrp_productions = super().create(vals_list)
        for mrp_production in mrp_productions:
            if mrp_production.task_id:
                mrp_production.message_post(
                    body=_("Manufacturing Order created from task %s", mrp_production.task_id._get_html_link())
                )
        return mrp_productions
