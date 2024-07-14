# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class BaseModuleUninstall(models.TransientModel):
    _inherit = "base.module.uninstall"

    is_studio = fields.Boolean(compute='_compute_is_studio')
    custom_views = fields.Integer(compute='_compute_custom_views')
    custom_reports = fields.Integer(compute='_compute_custom_reports')
    custom_models = fields.Integer(compute='_compute_custom_models')
    custom_fields = fields.Integer(compute='_compute_custom_fields')

    @api.depends('module_ids')
    def _compute_is_studio(self):
        for wizard in self:
            wizard.is_studio = 'web_studio' in wizard.module_ids.mapped('name')

    @api.depends('module_ids')
    def _compute_custom_views(self):
        for wizard in self:
            view_ids = self.env['ir.model.data'].search([
                ('module', '=', 'studio_customization'),
                ('model', '=', 'ir.ui.view'),
            ]).mapped('res_id')
            wizard.custom_views = self.env['ir.ui.view'].search_count([
                ('id', 'in', view_ids),
                ('type', '!=', 'qweb'),
            ])

    @api.depends('module_ids')
    def _compute_custom_reports(self):
        for wizard in self:
            wizard.custom_reports = self.env['ir.model.data'].search_count([
                ('module', '=', 'studio_customization'),
                ('model', '=', 'ir.actions.report'),
            ])

    def _get_models(self):
        # Overridden to include customizations made with studio
        res = super()._get_models()
        if self.is_studio:
            res |= self.env['ir.model'].search([
                ('transient', '=', False),
                ('state', '=', 'manual')
            ])
        return res

    @api.depends('model_ids')
    def _compute_custom_models(self):
        for wizard in self:
            wizard.custom_models = len(wizard.model_ids.filtered(lambda x: x.state == 'manual'))

    @api.depends('module_ids')
    def _compute_custom_fields(self):
        for wizard in self:
            wizard.custom_fields = self.env['ir.model.fields'].search_count([
                ('state', '=', 'manual'),
            ])
