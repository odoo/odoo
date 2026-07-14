from odoo import fields, models


class L10nTrNilveraAlias(models.Model):
    _name = 'l10n_tr.nilvera.alias'
    _description = "Customer Alias on Nilvera"

    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
