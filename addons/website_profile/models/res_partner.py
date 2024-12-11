# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    cover_image = fields.Image("Cover Image", store=True, readonly=False)
