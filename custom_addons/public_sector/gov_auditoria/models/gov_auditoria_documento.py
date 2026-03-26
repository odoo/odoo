import base64
import hashlib

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovAuditoriaDocumento(models.Model):
    _name = "gov.auditoria.documento"
    _description = "Audit Dossier Document"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    event_id = fields.Many2one("gov.auditoria.evento", ondelete="set null")
    nome = fields.Char(required=True, tracking=True)
    tipo = fields.Selection(
        [
            ("anexo_4320", "Anexo 4.320"),
            ("oficio", "Oficio"),
            ("notificacao", "Notificacao"),
            ("defesa", "Defesa"),
            ("recurso", "Recurso"),
            ("acordao", "Acordao"),
            ("certidao", "Certidao"),
            ("relatorio", "Relatorio"),
            ("balancete", "Balancete"),
            ("declaracao", "Declaracao"),
            ("outro", "Outro"),
        ],
        required=True,
        default="outro",
    )
    anexo_4320_numero = fields.Selection(
        [(str(number), f"Anexo {number}") for number in range(1, 18)],
        string="Numero do Anexo",
    )
    origem = fields.Selection(
        [
            ("gerado_odoo", "Gerado no Odoo"),
            ("importado", "Importado"),
            ("manual", "Manual"),
            ("legado", "Legado"),
        ],
        required=True,
        default="manual",
    )
    attachment_id = fields.Many2one("ir.attachment", ondelete="set null")
    hash_sha256 = fields.Char(copy=False)
    data_envio = fields.Datetime()
    protocolo_externo = fields.Char()
    versao = fields.Integer(default=1, required=True)
    versao_anterior_id = fields.Many2one("gov.auditoria.documento", ondelete="set null")
    state = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("finalizado", "Finalizado"),
            ("enviado", "Enviado"),
            ("substituido", "Substituido"),
        ],
        default="rascunho",
        required=True,
    )

    @api.constrains("tipo", "anexo_4320_numero")
    def _check_anexo_numero(self):
        for rec in self:
            if rec.tipo == "anexo_4320" and not rec.anexo_4320_numero:
                raise ValidationError("Informe o numero do anexo 4.320.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._compute_attachment_hash()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "attachment_id" in vals:
            self._compute_attachment_hash()
        return result

    def _compute_attachment_hash(self):
        for rec in self.filtered("attachment_id"):
            raw = base64.b64decode(rec.attachment_id.datas or b"")
            rec.hash_sha256 = hashlib.sha256(raw).hexdigest() if raw else False
