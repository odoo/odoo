from odoo import api, fields, models


class OctroiDeMerCode(models.Model):
    _name = 'l10n_fr.octroi.de.mer.code'
    _description = "Octroi de Mer Code"
    _order = 'code'

    code = fields.Char(string="Border reference")
    description = fields.Char()
    company_id = fields.Many2one(comodel_name='res.company')
    om_rate_id = fields.Many2one(
        comodel_name='account.tax',
        string="Octroi de Mer",
        domain=[
            ('tax_group_id.l10n_fr_om_rate', '=', 'general'),
            ('company_id', '=', company_id),
        ],
    )
    omr_rate_id = fields.Many2one(
        comodel_name='account.tax',
        string="Octroi de Mer Regional",
        domain=[
            ('tax_group_id.l10n_fr_om_rate', '=', 'regional'),
            ('company_id', '=', company_id),
        ],
    )

    _sql_constraints = [
        ('company_unique_code', 'UNIQUE(code, company_id)', "Code must be unique per company"),
    ]

    @api.depends('code', 'description')
    def _compute_display_name(self):
        for code in self:
            code.display_name = f"{code.code} - {code.description}"
