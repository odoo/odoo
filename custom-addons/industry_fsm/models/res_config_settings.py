# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_industry_fsm_report = fields.Boolean("Worksheets")
    module_industry_fsm_sale = fields.Boolean(
        string="Time and Material Invoicing",
        compute='_compute_module_industry_fsm_sale',
        store=True,
        readonly=False)
    group_industry_fsm_quotations = fields.Boolean(
        string="Extra Quotations",
        implied_group="industry_fsm.group_fsm_quotation_from_task",
        compute='_compute_group_industry_fsm_quotations',
        store=True,
        readonly=False)

    @api.model
    def _get_basic_project_domain(self):
        return expression.AND([super()._get_basic_project_domain(), [('is_fsm', '=', False)]])

    @api.depends('group_industry_fsm_quotations')
    def _compute_module_industry_fsm_sale(self):
        for config in self:
            if config.group_industry_fsm_quotations:
                config.module_industry_fsm_sale = True

    @api.depends('module_industry_fsm_sale')
    def _compute_group_industry_fsm_quotations(self):
        for config in self:
            if not config.module_industry_fsm_sale:
                config.group_industry_fsm_quotations = False
