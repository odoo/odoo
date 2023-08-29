# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    sale_header = fields.Binary(string="Header pages")
    sale_footer = fields.Binary(string="Footer pages")
