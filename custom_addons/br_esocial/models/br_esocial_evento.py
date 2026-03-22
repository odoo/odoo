from odoo import fields, models


class BrEsocialEvento(models.Model):
    _name = "br.esocial.evento"
    _description = "Evento eSocial"

    company_id = fields.Many2one("res.company", required=True, ondelete="cascade")
    tipo = fields.Char(required=True)
    nrRec = fields.Char()
    status = fields.Selection(
        [("pendente", "Pendente"), ("enviado", "Enviado"), ("processado", "Processado"), ("erro", "Erro"), ("excluido", "Excluido")],
        default="pendente",
    )
    xml_gerado = fields.Text()
    xml_retorno = fields.Text()
    data_envio = fields.Datetime()
    motivo_erro = fields.Text()

    def gerar_xml(self) -> bytes:
        return f"<eSocial><evt>{self.tipo}</evt></eSocial>".encode()

    def enviar(self):
        self.write({"status": "enviado", "data_envio": fields.Datetime.now()})

    def consultar(self):
        return {"status": self.status}

    def excluir(self):
        self.write({"status": "excluido"})

