###################################################################################
#
#    Copyright (c) 2017-today MuK IT GmbH.
#
#    This file is part of MuK Backend Theme
#    (see https://mukit.at).
#
#    MuK Proprietary License v1.0
#
#    This software and associated files (the "Software") may only be used
#    (executed, modified, executed after modifications) if you have
#    purchased a valid license from MuK IT GmbH.
#
#    The above permissions are granted for a single database per purchased
#    license. Furthermore, with a valid license it is permitted to use the
#    software on other databases as long as the usage is limited to a testing
#    or development environment.
#
#    You may develop modules based on the Software or that use the Software
#    as a library (typically by depending on it, importing it and using its
#    resources), but without copying any source code or material from the
#    Software. You may distribute those modules under the license of your
#    choice, provided that this license is compatible with the terms of the
#    MuK Proprietary License (For example: LGPL, MIT, or proprietary licenses
#    similar to this one).
#
#    It is forbidden to publish, distribute, sublicense, or sell copies of
#    the Software or modified copies of the Software.
#
#    The above copyright notice and this permission notice must be included
#    in all copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###################################################################################

import re
import uuid
import base64

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    theme_favicon = fields.Binary(
        related='company_id.favicon',
        readonly=False
    )
    
    theme_background_image = fields.Binary(
        related='company_id.background_image',
        readonly=False
    )
    
    theme_color_brand = fields.Char(
        string='Theme Brand Color'
    )
    
    theme_color_primary = fields.Char(
        string='Theme Primary Color'
    )
    
    theme_color_menu = fields.Char(
        string='Theme Menu Color'
    )
    
    theme_color_appbar_color = fields.Char(
        string='Theme AppBar Color'
    )
    
    theme_color_appbar_background = fields.Char(
        string='Theme AppBar Background'
    )
    
    #----------------------------------------------------------
    # Action
    #----------------------------------------------------------
    
    def action_reset_theme_assets(self):
        self.env['web_editor.assets'].reset_asset(
            '/muk_web_theme/static/src/colors.scss', 'web._assets_primary_variables',
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        variables = [
            'o-brand-odoo',
            'o-brand-primary',
            'mk-menu-color',
            'mk-appbar-color',
            'mk-appbar-background',
        ]
        colors = self.env['web_editor.assets'].get_theme_variables_values(
            '/muk_web_theme/static/src/colors.scss', 'web._assets_primary_variables', variables
        )
        colors_changed = []
        colors_changed.append(self.theme_color_brand != colors['o-brand-odoo'])
        colors_changed.append(self.theme_color_primary != colors['o-brand-primary'])
        colors_changed.append(self.theme_color_menu != colors['mk-menu-color'])
        colors_changed.append(self.theme_color_appbar_color != colors['mk-appbar-color'])
        colors_changed.append(self.theme_color_appbar_background != colors['mk-appbar-background'])
        if(any(colors_changed)):
            variables = [
                {'name': 'o-brand-odoo', 'value': self.theme_color_brand or "#243742"},
                {'name': 'o-brand-primary', 'value': self.theme_color_primary or "#5D8DA8"},
                {'name': 'mk-menu-color', 'value': self.theme_color_menu or "#f8f9fa"},
                {'name': 'mk-appbar-color', 'value': self.theme_color_appbar_color or "#dee2e6"},
                {'name': 'mk-appbar-background', 'value': self.theme_color_appbar_background or "#000000"},
            ]
            self.env['web_editor.assets'].replace_theme_variables_values(
                '/muk_web_theme/static/src/colors.scss', 'web._assets_primary_variables', variables
            )
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        variables = [
            'o-brand-odoo',
            'o-brand-primary',
            'mk-menu-color',
            'mk-appbar-color',
            'mk-appbar-background',
        ]
        colors = self.env['web_editor.assets'].get_theme_variables_values(
            '/muk_web_theme/static/src/colors.scss', 'web._assets_primary_variables', variables
        )
        res.update({
            'theme_color_brand': colors['o-brand-odoo'],
            'theme_color_primary': colors['o-brand-primary'],
            'theme_color_menu': colors['mk-menu-color'],
            'theme_color_appbar_color': colors['mk-appbar-color'],
            'theme_color_appbar_background': colors['mk-appbar-background'],
        })
        return res
