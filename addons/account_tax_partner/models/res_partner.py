# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tax_ids = fields.One2many(
        'res.partner.tax',
        'partner_id',
        'Taxes',
    )
