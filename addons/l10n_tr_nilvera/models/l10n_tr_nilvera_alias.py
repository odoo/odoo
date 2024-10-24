from odoo import fields, models


class Alias(models.Model):
    _name = 'l10n_tr.nilvera.alias'

    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
