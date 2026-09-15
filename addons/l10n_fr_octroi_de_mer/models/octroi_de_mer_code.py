from odoo import api, fields, models


class OctroiDeMerCode(models.Model):
    _name = 'l10n_fr.octroi.de.mer.code'
    _description = "Octroi de Mer Code"
    _order = 'code'

    code = fields.Char(string="Border reference")
    description = fields.Char()
    om_rate_id = fields.Many2one(
        comodel_name='account.tax',
        string="Octroi de Mer",
        domain=[('tax_group_id.l10n_fr_om_rate', '=', 'general')],
    )
    omr_rate_id = fields.Many2one(
        comodel_name='account.tax',
        string="Octroi de Mer Regional",
        domain=[('tax_group_id.l10n_fr_om_rate', '=', 'regional')],
    )

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', "Code must be unique"),
    ]

    @api.depends('code', 'description')
    def _compute_display_name(self):
        for code in self:
            code.display_name = f"{code.code} - {code.description}"
