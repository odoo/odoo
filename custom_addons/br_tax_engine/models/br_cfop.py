from odoo import fields, models


class BrCfop(models.Model):
    _name = "br.cfop"
    _description = "CFOP Brasileiro"
    _order = "code"

    code = fields.Char(required=True, size=4)
    name = fields.Char(required=True)
    tipo = fields.Selection(
        [
            ("1", "Entrada Estadual"),
            ("2", "Entrada Interestadual"),
            ("3", "Entrada Exterior"),
            ("5", "Saida Estadual"),
            ("6", "Saida Interestadual"),
            ("7", "Saida Exterior"),
        ],
        required=True,
    )
    aplicacao = fields.Text()
    date_from = fields.Date(required=True)
    date_to = fields.Date()

    _sql_constraints = [("br_cfop_code_unique", "unique(code)", "O codigo CFOP deve ser unico.")]

