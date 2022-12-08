# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    task_id = fields.Many2one('project.task', string='Task')

    @api.model_create_multi
    def create(self, vals_list):
        mrp_productions = super().create(vals_list)
        for mrp_production in mrp_productions:
            if mrp_production.task_id:
                mrp_production.message_post(body=_("Manufacturing Order created from task %s", f"<a href='#' data-oe-model='project.task' data-oe-id='{mrp_production.task_id.id}'>{mrp_production.task_id.name}</a>"))
        return mrp_productions
