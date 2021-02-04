# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WebsiteConfiguratorFeature(models.Model):

    _name = 'website.configurator.feature'
    _description = 'Website Configurator Feature'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(translate=True)
    description = fields.Char(translate=True)
    icon = fields.Char()
    iap_page_code = fields.Char(help='Page code used to tell IAP website_service for which page a snippet list should be generated')
    website_types_preselection = fields.Char(help='Comma-separated list of website type for which this feature should be pre-selected')
    type = fields.Selection([('page', "Page"), ('app', "App")], compute='_compute_type')
    page_view_id = fields.Many2one('ir.ui.view', ondelete='cascade')
    module_id = fields.Many2one('ir.module.module', ondelete='cascade')

    @api.depends('module_id', 'page_view_id')
    def _compute_type(self):
        for record in self:
            record.type = 'page' if record.page_view_id else 'app'

    @api.constrains('module_id', 'page_view_id')
    def _check_module_xor_page_view(self):
        if bool(self.module_id) == bool(self.page_view_id):
            raise ValidationError(_("One and only one of the two fields 'page_view_id' and 'module_id' should be set"))
