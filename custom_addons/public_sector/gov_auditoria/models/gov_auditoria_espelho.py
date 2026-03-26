from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovAuditoriaEspelho(models.Model):
    _name = "gov.auditoria.espelho"
    _description = "Historical Mirror Entry"
    _order = "data_movimento desc, id desc"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="ciclo_id.currency_id", store=True, readonly=True)
    tipo_movimento = fields.Selection(
        [
            ("receita", "Receita"),
            ("despesa", "Despesa"),
            ("empenho", "Empenho"),
            ("liquidacao", "Liquidacao"),
            ("pagamento", "Pagamento"),
            ("saldo", "Saldo"),
        ],
        required=True,
        default="despesa",
    )
    data_movimento = fields.Date(required=True, default=fields.Date.today)
    valor = fields.Monetary(required=True, currency_field="currency_id")
    historico = fields.Text(required=True)
    origem = fields.Selection(
        [
            ("importado_csv", "Importado CSV"),
            ("migracao_api", "Migracao API"),
            ("lancamento_manual", "Lancamento Manual"),
        ],
        required=True,
        default="lancamento_manual",
    )
    documento_fonte_id = fields.Many2one("ir.attachment", ondelete="set null")
    hash_fonte = fields.Char()
    conta_codigo = fields.Char()
    conta_odoo_id = fields.Many2one("account.account", ondelete="set null")
    fonte_recurso = fields.Char()
    natureza_despesa = fields.Char()
    funcional = fields.Char()
    validado = fields.Boolean(default=False)
    validado_por = fields.Many2one("res.users", readonly=True)
    data_validacao = fields.Datetime(readonly=True)
    obs_validacao = fields.Text()

    @api.constrains("origem", "documento_fonte_id")
    def _check_required_source_document(self):
        for rec in self:
            if rec.origem in ("importado_csv", "migracao_api") and not rec.documento_fonte_id:
                raise ValidationError("Registros importados exigem documento fonte.")

    def action_validate_entry(self):
        for rec in self:
            rec.write(
                {
                    "validado": True,
                    "validado_por": self.env.user.id,
                    "data_validacao": fields.Datetime.now(),
                }
            )
        return True

    def write(self, vals):
        if not self.env.user.has_group("gov_auditoria.group_auditoria_admin"):
            locked_entries = self.filtered("validado")
            if locked_entries:
                raise ValidationError("Registros de espelho validados sao imutaveis para este perfil.")
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group("gov_auditoria.group_auditoria_admin"):
            locked_entries = self.filtered("validado")
            if locked_entries:
                raise ValidationError("Registros de espelho validados nao podem ser removidos.")
        return super().unlink()
