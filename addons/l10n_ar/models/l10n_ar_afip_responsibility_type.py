# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class L10nArAfipResponsibilityType(models.Model):

    _name = 'l10n_ar.afip.responsibility.type'
    _description = 'AFIP Responsibility Type'
    _order = 'sequence'

    name = fields.Char(required=True, index=True)
    sequence = fields.Integer()
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'),
                        ('code', 'unique(code)', 'Code must be unique!')]
