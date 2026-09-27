# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class L10n_ArAfipResponsibilityType(models.Model):
    _name = 'l10n_ar.afip.responsibility.type'

    _description = 'ARCA Responsibility Type'
    _order = 'sequence'

    name = fields.Char(required=True, index='trigram')
    sequence = fields.Integer()
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint('unique(name)', 'Name must be unique!')
    _code_uniq = models.Constraint('unique(code)', 'Code must be unique!')
