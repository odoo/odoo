# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class L10nBRCustomsRegime(models.Model):
    _name = 'l10n_br.customs.regime'
    _description = 'Special Brazilian customs regime'

    name = fields.Char('Name', required=True)
