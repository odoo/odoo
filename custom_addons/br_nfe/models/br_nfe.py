from odoo import fields, models


class BrNfe(models.Model):
    _name = "br.nfe"
    _description = "Nota Fiscal Eletronica"

    account_move_id = fields.Many2one("account.move", ondelete="cascade")
    company_id = fields.Many2one("res.company", required=True, ondelete="cascade")
    numero = fields.Integer()
    serie = fields.Char(size=3)
    chave_acesso = fields.Char(size=44)
    protocolo = fields.Char()
    ambiente = fields.Selection([("1", "Producao"), ("2", "Homologacao")], default="2")
    estado = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("validando", "Validando"),
            ("enviando", "Enviando"),
            ("autorizado", "Autorizado"),
            ("rejeitado", "Rejeitado"),
            ("cancelado", "Cancelado"),
            ("inutilizado", "Inutilizado"),
            ("contingencia", "Contingencia"),
        ],
        default="rascunho",
    )
    xml_assinado = fields.Text()
    xml_retorno = fields.Text()
    danfe_pdf = fields.Binary()
    contingencia_tipo = fields.Selection([("scan", "SCAN"), ("svc_an", "SVC-AN"), ("svc_rs", "SVC-RS")])
    motivo_cancelamento = fields.Char()
    data_emissao = fields.Datetime()
    data_autorizacao = fields.Datetime()
    data_cancelamento = fields.Datetime()

    def action_validar(self):
        self.write({"estado": "validando"})

    def action_assinar(self):
        self.ensure_one()
        from ..services.br_nfe_xml_generator import BrNfeXmlGenerator

        self.xml_assinado = BrNfeXmlGenerator().generate(self).decode()
        self.estado = "validando"

    def action_enviar(self):
        self.write({"estado": "enviando"})

    def action_consultar(self):
        return {"estado": self.estado}

    def action_cancelar(self):
        self.write({"estado": "cancelado", "data_cancelamento": fields.Datetime.now()})

    def action_inutilizar(self):
        self.write({"estado": "inutilizado"})

    def action_contingencia(self):
        self.write({"estado": "contingencia"})

