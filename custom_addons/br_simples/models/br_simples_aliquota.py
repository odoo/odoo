from odoo import fields, models


class BrSimplesAliquota(models.Model):
    _name = "br.simples.aliquota"
    _description = "Faixa de Aliquota do Simples"
    _order = "anexo_id, receita_min"

    anexo_id = fields.Many2one("br.simples.anexo", required=True, ondelete="cascade")
    receita_min = fields.Float(required=True)
    receita_max = fields.Float(required=True)
    aliquota_nominal = fields.Float(required=True)
    valor_deduzir = fields.Float()

    def calcular_aliquota_efetiva(self, rbt12):
        if not rbt12:
            return 0.0
        self.ensure_one()
        return ((rbt12 * self.aliquota_nominal) - self.valor_deduzir) / rbt12
