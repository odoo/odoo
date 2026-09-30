from odoo import api, fields, models


class L10nRoCPVCode(models.Model):
    _name = "l10n_ro.cpv.code"
    _description = "CPV Code"

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)

    _code_uniq = models.Constraint(
        'unique (code)',
        'Code must be unique!',
    )

    @api.depends('code')
    def _compute_display_name(self):
        for cpv in self:
            cpv.display_name = f"{cpv.code} {cpv.name or ''}"
