# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sign_terms = fields.Html(related='company_id.sign_terms', string="Sign Terms & Conditions", readonly=False)
    sign_terms_html = fields.Html(related='company_id.sign_terms_html', string="Sign Terms & Conditions as a Web page",
        readonly=False)
    sign_terms_type = fields.Selection(
        related='company_id.sign_terms_type', readonly=False)
    sign_preview_ready = fields.Boolean(string="Display sign preview button", compute='_compute_sign_terms_preview')

    use_sign_terms = fields.Boolean(
        string='Sign Default Terms & Conditions',
        config_parameter='sign.use_sign_terms',
        default=False)

    group_manage_template_access = fields.Boolean(string="Manage template access", implied_group='sign.manage_template_access')

    module_sign_itsme = fields.Boolean(string="Identify with itsme®")

    @api.depends('sign_terms_type')
    def _compute_sign_terms_preview(self):
        for setting in self:
            # We display the preview button only if the terms_type is html in the setting but also on the company
            # to avoid landing on an error page (see terms.py controller)
            setting.sign_preview_ready = self.env.company.sign_terms_type == 'html' and setting.sign_terms_type == 'html'
