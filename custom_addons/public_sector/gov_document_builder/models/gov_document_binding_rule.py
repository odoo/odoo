from odoo import fields, models


class GovDocumentBindingRule(models.Model):
    """Define regras reutilizáveis de binding entre dados fonte e blocos."""

    _name = "gov.document.binding.rule"
    _description = "Regra de Binding de Documento"
    _order = "name asc, id asc"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    source_model = fields.Char(string="Modelo Fonte")
    source_path = fields.Char(string="Caminho do Campo")
    transformer = fields.Char(
        string="Transformador",
        help="strip, upper, date_br, currency_br, etc.",
    )
    fallback_value = fields.Char(string="Valor Padrão")
    output_kind = fields.Selection(
        [
            ("text", "Texto"),
            ("date", "Data"),
            ("currency", "Moeda"),
            ("html", "HTML"),
        ],
        default="text",
        string="Tipo de Saída",
    )
    active = fields.Boolean(default=True)
