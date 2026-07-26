# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    stripe_customer_id = fields.Char(string="Stripe Customer ID", copy=False)
