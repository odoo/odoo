from odoo import fields, models


class BrIrrfTabela(models.Model):
    _name = "br.irrf.tabela"
    _description = "Tabela IRRF"

    date_from = fields.Date(required=True)
    date_to = fields.Date()
    deducao_por_dependente = fields.Float()
    linha_ids = fields.One2many("br.irrf.tabela.linha", "tabela_id")

    def calcular(self, base, n_dependentes, data_desconto=None, date=None):
        self.ensure_one()
        base_ajustada = max(base - (n_dependentes * self.deducao_por_dependente), 0.0)
        for linha in self.linha_ids.sorted("base_calculo_min"):
            if linha.base_calculo_min <= base_ajustada <= linha.base_calculo_max:
                return max((base_ajustada * linha.aliquota) - linha.parcela_deduzir, 0.0)
        return 0.0


class BrIrrfTabelaLinha(models.Model):
    _name = "br.irrf.tabela.linha"
    _description = "Linha Tabela IRRF"

    tabela_id = fields.Many2one("br.irrf.tabela", required=True, ondelete="cascade")
    base_calculo_min = fields.Float(required=True)
    base_calculo_max = fields.Float(required=True)
    aliquota = fields.Float(required=True)
    parcela_deduzir = fields.Float()

