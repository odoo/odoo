# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartnerGrade(models.Model):
    _name = 'res.partner.grade'
    _order = 'sequence'
    _description = 'Partner Grade'

    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    name = fields.Char('Level Name', translate=True)
