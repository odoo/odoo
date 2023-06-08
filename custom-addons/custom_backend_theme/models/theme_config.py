from odoo import fields, models


class ThemeConfig(models.Model):
    _name = 'custom_theme'

    name = fields.Char(string='Name')
