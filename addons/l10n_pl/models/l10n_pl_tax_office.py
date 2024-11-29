from odoo import api, fields, models


class L10n_PlL10n_Pl_Tax_Office(models.Model):
    _name = 'l10n_pl.l10n_pl_tax_office'
    _description = 'Tax Office in Poland'
    _rec_names_search = ['name', 'code']
    _order = 'code'

    code = fields.Char('Code', required=True)
    name = fields.Char('Description', required=True)

    _code_company_uniq = models.Constraint(
        'unique (code)',
        'The code of the tax office must be unique !',
    )

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for tax_office in self:
            tax_office.display_name = f'{tax_office.code} {tax_office.name}'
