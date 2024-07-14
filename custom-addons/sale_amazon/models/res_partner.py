# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    amazon_email = fields.Char(help="The encrypted email of the customer. Does not forward mails.")
