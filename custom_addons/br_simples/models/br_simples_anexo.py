from odoo import fields, models


class BrSimplesAnexo(models.Model):
    _name = "br.simples.anexo"
    _description = "Anexo do Simples Nacional"
    _order = "code, date_from desc"

    code = fields.Selection([("I", "I"), ("II", "II"), ("III", "III"), ("IV", "IV"), ("V", "V")], required=True)
    name = fields.Char(required=True)
    descricao = fields.Text()
    date_from = fields.Date(required=True)
    date_to = fields.Date()

