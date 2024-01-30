from odoo import fields, models


class TaxOffice(models.Model):
    _name = 'l10n_pl_tax_office'
    _description = 'Tax Office in Poland'
    _rec_names_search = ['name', 'code']
    _order = 'code'

    code = fields.Char('Code', required=True)
    name = fields.Char('Description', required=True)

    _sql_constraints = [
        ('code_company_uniq', 'unique (code)', 'The code of the tax office must be unique !')
    ]

    def name_get(self):
        result = []
        for tax_office in self:
            name = tax_office.code + ' ' + tax_office.name
            result.append((tax_office.id, name))
        return result
