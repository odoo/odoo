# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    paperformat_id = fields.Many2one(related="company_id.paperformat_id", string='Paper format')
    default_report_template = fields.Selection(related="company_id.default_report_template")

    def _prepare_report_view_action(self, template):
        template_id = self.env.ref(template)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.view',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': template_id.id,
        }

    def edit_external_header(self):
        template = self.default_report_template
        if template=='standard': template='default'
        return self._prepare_report_view_action('report.report_template_'+template)
