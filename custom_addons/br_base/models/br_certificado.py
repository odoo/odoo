from odoo import api, fields, models

from ..services.br_sign_service import BrSignService


class BrCertificado(models.Model):
    _name = "br.certificado"
    _description = "Certificado Digital Brasileiro"
    _order = "validade desc, id desc"

    company_id = fields.Many2one("res.company", required=True, ondelete="cascade")
    tipo = fields.Selection(
        [("a1", "A1 - Arquivo .pfx"), ("a3", "A3 - Token/Smartcard")],
        required=True,
        default="a1",
    )
    arquivo_pfx = fields.Binary()
    senha = fields.Char(groups="br_base.group_manager")
    validade = fields.Date()
    titular = fields.Char()
    estado = fields.Selection(
        [("ativo", "Ativo"), ("expirado", "Expirado"), ("revogado", "Revogado")],
        default="ativo",
        compute="_compute_estado",
        store=True,
    )

    @api.depends("validade")
    def _compute_estado(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.validade and record.validade < today:
                record.estado = "expirado"
            else:
                record.estado = "ativo"

    @api.onchange("arquivo_pfx", "senha")
    def _onchange_extract_metadata(self):
        service = BrSignService()
        for record in self.filtered(lambda cert: cert.tipo == "a1" and cert.arquivo_pfx and cert.senha):
            metadata = service.extract_certificate_metadata(record.arquivo_pfx, record.senha)
            if metadata:
                record.validade = metadata.get("validade")
                record.titular = metadata.get("titular")

