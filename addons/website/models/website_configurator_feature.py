# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.modules.module import get_resource_path


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
        preview_svg = get_resource_path(theme, 'static', 'description', theme + '.svg')
        if not preview_svg:
            return False
        with tools.file_open(preview_svg, 'r') as file:
            svg = file.read()

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
        color_regex = '(?i)%s' % '|'.join('(%s)' % color for color in color_mapping.keys())
        image_regex = '(?i)%s' % '|'.join('(%s)' % image for image in image_mapping.keys())

        def subber_maker(mapping):
            def subber(match):
                key = match.group()
                return mapping[key] if key in mapping else key
            return subber

        svg = re.sub(color_regex, subber_maker(color_mapping), svg)
        svg = re.sub(image_regex, subber_maker(image_mapping), svg)
        return svg
