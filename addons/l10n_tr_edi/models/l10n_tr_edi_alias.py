from odoo import fields, models


class L10n_Tr_EdiAlias(models.Model):
    _name = 'l10n_tr_edi.alias'
    _description = "GİB Customer Alias"

    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
