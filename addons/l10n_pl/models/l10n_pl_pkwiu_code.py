from odoo import api, fields, models


class L10nPlPKWiUCode(models.Model):
    '''
    Codes used for the Polish Classification of Products and Services.

    You can find the list of codes here: https://klasyfikacje.stat.gov.pl/static/pkwiu_25/pdf/KlasyfikacjaPKWiU2025.pdf
    '''
    _name = 'l10n_pl.pkwiu.code'
    _description = 'PKWiU Code'
    _order = "code"
    _rec_names_search = ('code', 'name')

    name = fields.Char()
    code = fields.Char(required=True)
    expiry_date = fields.Date(
        string='Expiry Date',
        help='Date at which a code must not be used anymore.',
    )
    start_date = fields.Date(
        string='Usage start date',
        help='Date from which a code may be used.',
    )
    l10n_pl_split_payment = fields.Boolean(string="Implies Split Payment")

    _code_unique = models.Constraint(
        'UNIQUE (code)',
        "The code must be unique.",
    )

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f'{record.code} {record.name}'
