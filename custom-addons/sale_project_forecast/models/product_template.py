# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    planning_enabled = fields.Boolean(compute="_compute_planning_enabled", readonly=False, store=True)

    @api.depends('service_policy')
    def _compute_planning_enabled(self):
        self.filtered(lambda template: template.service_policy in ['delivered_manual', 'delivered_milestones']).planning_enabled = False
