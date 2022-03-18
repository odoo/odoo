# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class L10nArAfipResponsibilityType(models.Model):

    _name = 'l10n_ar.afip.responsibility.type'
    _description = 'AFIP Responsibility Type'
    _order = 'sequence'

    name = fields.Char(required=True, index='unique')
    sequence = fields.Integer()
    code = fields.Char(required=True, index='unique')
    active = fields.Boolean(default=True)
