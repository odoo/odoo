# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class ThemeConfig(models.Model):
    """Model for storing configuration settings related to the theme"""
    _name = 'theme.config'
    _description = "Model for storing configuration related to the theme"

    name = fields.Char(help="Theme name")
    theme_main_color = fields.Char(help="main theme color")
    view_font_color = fields.Char(help="backend font color")
    theme_font_color = fields.Char(help="backend view font color")
    login_background_color = fields.Char(
        help="login page background color",
        default="#f1f4f5",
    )
    is_theme_active = fields.Boolean(string="Active Theme")

    @api.model
    def create_new_theme(self):
        """function to create a new theme"""
        theme_obj = self.create({
            'theme_main_color': '#6fb702',
            'view_font_color': '#333',
            'theme_font_color': '#fff',
            'login_background_color': '#f1f4f5',
            'is_theme_active': False,
        })
        theme_obj.name = 'Theme ' + str(theme_obj.id)
        return theme_obj.read(['name', 'theme_main_color', 'view_font_color',
                               'theme_font_color', 'login_background_color',
                               'is_theme_active'])

    @api.model
    def update_active_theme(self, theme_id):
        """function to update active theme"""
        theme = {}
        for record in self.search([]):
            if record.is_theme_active:
                theme['prev'] = record.id
            record.is_theme_active = record.id == theme_id
        return theme
