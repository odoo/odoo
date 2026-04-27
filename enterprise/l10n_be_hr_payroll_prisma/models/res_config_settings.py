# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    prisma_code = fields.Char(
        related='company_id.prisma_code', string="Prisma Affiliation Number", readonly=False)
