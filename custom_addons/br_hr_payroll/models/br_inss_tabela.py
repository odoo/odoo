from odoo import fields, models


class BrInssTabela(models.Model):
    _name = "br.inss.tabela"
    _description = "Tabela INSS"

    date_from = fields.Date(required=True)
    date_to = fields.Date()
    linha_ids = fields.One2many("br.inss.tabela.linha", "tabela_id")

    def calcular(self, salario_bruto, date=None):
        self.ensure_one()
        total = 0.0
        for linha in self.linha_ids.sorted("salario_min"):
            if salario_bruto <= linha.salario_min:
                continue
            faixa_max = min(salario_bruto, linha.salario_max or salario_bruto)
            base = max(faixa_max - linha.salario_min, 0.0)
            total += base * linha.aliquota
        return total


class BrInssTabelaLinha(models.Model):
    _name = "br.inss.tabela.linha"
    _description = "Linha Tabela INSS"

    tabela_id = fields.Many2one("br.inss.tabela", required=True, ondelete="cascade")
    salario_min = fields.Float(required=True)
    salario_max = fields.Float()
    aliquota = fields.Float(required=True)

