from odoo import fields, models


class BrMunicipio(models.Model):
    _name = "br.municipio"
    _description = "Municipio Brasileiro"
    _order = "name"
    _rec_name = "display_name"

    name = fields.Char(required=True)
    code_ibge = fields.Char(required=True, index=True)
    state_id = fields.Many2one(
        "res.country.state",
        string="UF",
        required=True,
        ondelete="restrict",
    )
    country_id = fields.Many2one(
        "res.country",
        related="state_id.country_id",
        store=True,
        readonly=True,
    )
    active = fields.Boolean(default=True)
    display_name = fields.Char(compute="_compute_display_name")

    _sql_constraints = [
        ("br_municipio_ibge_unique", "unique(code_ibge)", "O codigo IBGE deve ser unico."),
    ]

    def _compute_display_name(self):
        for record in self:
            suffix = record.state_id.code or ""
            record.display_name = f"{record.name}/{suffix}" if suffix else record.name

