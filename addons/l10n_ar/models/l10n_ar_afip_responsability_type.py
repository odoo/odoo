# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class L10nArAfipResponsabilityType(models.Model):

    _name = 'l10n_ar.afip.responsability.type'
    _description = 'AFIP Responsability Type'
    _order = 'sequence'

    name = fields.Char(required=True, index=True)
    sequence = fields.Integer()
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'),
                        ('code', 'unique(code)', 'Code must be unique!')]
