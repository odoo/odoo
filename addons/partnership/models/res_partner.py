# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    grade_id = fields.Many2one('res.partner.grade', 'Partner Level', tracking=True)
