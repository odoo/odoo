# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteConfiguratorFeature(models.Model):
    _name = 'website.configurator.feature'

    _description = 'Website Configurator Feature'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(translate=True)
    description = fields.Char(translate=True)
    icon = fields.Char()
    website_config_preselection = fields.Char(help='Comma-separated list of website type/purpose for which this feature should be pre-selected')
    module_id = fields.Many2one('ir.module.module', ondelete='cascade')
    feature_url = fields.Char()
    menu_sequence = fields.Integer(help='If set, a website menu will be created for the feature.')
    menu_company = fields.Boolean(help='If set, add the menu as a second level menu, as a child of "Company" menu.')
