# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, tools, _
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
    website_config_preselection = fields.Char(help='Comma-separated list of website type/purpose for which this feature should be pre-selected')
    page_view_id = fields.Many2one('ir.ui.view', ondelete='cascade')
    module_id = fields.Many2one('ir.module.module', ondelete='cascade')
    feature_url = fields.Char()
    menu_sequence = fields.Integer(help='If set, a website menu will be created for the feature.')
    menu_company = fields.Boolean(help='If set, add the menu as a second level menu, as a child of "Company" menu.')

    @api.constrains('module_id', 'page_view_id')
    def _check_module_xor_page_view(self):
        if bool(self.module_id) == bool(self.page_view_id):
            raise ValidationError(_("One and only one of the two fields 'page_view_id' and 'module_id' should be set"))

    @staticmethod
    def _process_svg(theme, colors, image_mapping):
        svg = None
        try:
            with tools.file_open(f'{theme}/static/description/{theme}.svg', 'r') as file:
                svg = file.read()
        except FileNotFoundError:
            return False

        default_colors = {
            'color1': '#3AADAA',
            'color2': '#7C6576',
            'color3': '#F6F6F6',
            'color4': '#FFFFFF',
            'color5': '#383E45',
            'menu': '#MENU_COLOR',
            'footer': '#FOOTER_COLOR',
        }
        color_mapping = {default_colors[color_key]: color_value for color_key, color_value in colors.items() if color_key in default_colors.keys()}

        # Replace the default colors by the chosen ones
        for default_color, chosen_color in color_mapping.items():
            svg = svg.replace(default_color, chosen_color)

        # Replace the default images by the one corresponding to the industry
        for default_img, new_img in image_mapping.items():
            svg = svg.replace(default_img, new_img)
        return svg
