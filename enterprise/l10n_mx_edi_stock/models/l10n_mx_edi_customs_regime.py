from odoo import fields, models


class MexicanEDICustomsRegime(models.Model):
    _name = 'l10n_mx_edi.customs.regime'
    _description = 'Mexican Customs Regime'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    goods_direction = fields.Selection(
        selection=[
            ('import', 'Import'),
            ('export', 'Export'),
            ('both', 'Import, Export'),
        ],
        string='Type',
        required=True,
    )

    _sql_constraints = [
        ('uniq_code', 'UNIQUE(code)', 'This code is already used.'),
    ]
