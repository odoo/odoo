from odoo import fields, models


class L10nCzTaxOffice(models.Model):
    _name = 'l10n_cz.tax_office'
    _description = 'Tax office in Czech Republic'
    _order = 'workplace_code ASC'
    _rec_names_search = ['workplace_code', 'name']

    workplace_code = fields.Integer(string="Territorial Office", required=True, aggregator=False)
    code = fields.Integer(string="Code", required=True, aggregator=False)
    name = fields.Char(string="Name", translate=True)
    region = fields.Char(string="Region", required=True, translate=True)

    _sql_constraints = [
        ('workplace_code_unique', 'UNIQUE (workplace_code)', "The territorial workplace code must be unique"),
    ]
