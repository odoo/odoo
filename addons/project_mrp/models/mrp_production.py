# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    task_id = fields.Many2one('project.task', string='Task', readonly=True, export_string_translation=False)

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        analytic_account = self.env['account.analytic.account']
        if self.env.context.get('task_id'):
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
                mrp_production.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': mrp_production, 'origin': mrp_production.task_id},
                    subtype_xmlid='mail.mt_note',
                )
        return mrp_productions
