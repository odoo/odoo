from odoo import fields, models


class BrNfeEndpoint(models.Model):
    _name = "br.nfe.endpoint"
    _description = "Endpoint SEFAZ por UF"
    _order = "uf, ambiente, servico"

    uf = fields.Char(size=2, required=True)
    ambiente = fields.Selection([("1", "Producao"), ("2", "Homologacao")], required=True)
    servico = fields.Selection(
        [
            ("NfeAutorizacao", "Autorizacao"),
            ("NfeRetAutorizacao", "Retorno Autorizacao"),
            ("NfeCancelamento", "Cancelamento"),
            ("NfeInutilizacao", "Inutilizacao"),
            ("NfeConsultaProtocolo", "Consulta"),
            ("NfeStatusServico", "Status"),
        ],
        required=True,
    )
    url = fields.Char(required=True)

