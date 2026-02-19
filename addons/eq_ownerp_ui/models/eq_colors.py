# -*- coding: utf-8 -*-
# Copyright 2014-now Equitania Software GmbH - Pforzheim - Germany
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _

class EqColors(models.Model):
    _name = "eq.colors"
    _description = 'Color Template'

    name = fields.Char(string="Name")
    # Basic Colors
    eq_basic_text_color = fields.Char(string="Basic Text Color")
    eq_basic_secondary_color = fields.Char(string="Basic Secondary Color")
    eq_link_color = fields.Char(string="Link Color")
    # Navigation
    eq_apps_color = fields.Char(string="App-Icon Color")
    eq_navi_background = fields.Char(string="Navigation Background")
    eq_navi_fontcolor = fields.Char(string="Navigation Fontcolor")
    eq_navi_hover = fields.Char(string="Navigation Hover Background")
    eq_navi_hover_fontcolor = fields.Char(string="Navigation Hover Font")
    # Buttons
    eq_btn_primary_background = fields.Char(string="Primary Button Backgroundcolor")
    eq_btn_primary_fontcolor = fields.Char(string="Primary Button Fontcolor")
    eq_btn_secondary_background = fields.Char(string="Secondary Button Backgroundcolor")
    eq_btn_secondary_fontcolor = fields.Char(string="Secondary Button Fontcolor")

    def unlink(self):
        for eq_colors in self:
            if self.env['ir.config_parameter'].get_param("eq_color_template_id") and int(self.env['ir.config_parameter'].get_param("eq_color_template_id")) == self.id:
                self.env['ir.config_parameter'].set_param("eq_color_template_id", False)
        return super(EqColors, self).unlink()