from odoo import api, fields, models
from odoo.exceptions import UserError


class GovProcessoVinculo(models.Model):
    _name = "gov.processo.vinculo"
    _description = "Vínculo entre Processo e Registro Financeiro"
    _order = "created_at desc"

    _MODEL_LABELS = {
        "gov.empenho": "Empenho (NE)",
        "gov.contrato": "Contrato",
        "gov.licitacao": "Licitação",
        "account.move": "Nota Fiscal / Liquidação",
        "account.payment": "Pagamento",
        "gov.processo": "Processo relacionado",
    }

    processo_id = fields.Many2one(
        "gov.processo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_name = fields.Char(
        string="Modelo",
        required=True,
        help="Nome técnico do modelo. Ex: gov.empenho, gov.contrato",
    )
    record_id = fields.Integer(string="ID do Registro", required=True)
    vinculo_type = fields.Selection(
        [
            ("instrui", "Instrui"),
            ("gera", "Gera"),
            ("arquiva", "Arquiva"),
            ("referencia", "Referência"),
        ],
        string="Tipo de Vínculo",
        required=True,
        default="instrui",
    )
    display_name_cached = fields.Char(
        string="Descrição do Registro",
        compute="_compute_display_name_cached",
        store=True,
    )
    model_label = fields.Char(string="Tipo", compute="_compute_model_label", store=False)
    created_at = fields.Datetime(string="Vinculado em", default=fields.Datetime.now)
    created_by = fields.Many2one(
        "res.users",
        string="Vinculado por",
        default=lambda self: self.env.user,
    )

    @api.depends("model_name")
    def _compute_model_label(self):
        for rec in self:
            rec.model_label = self._MODEL_LABELS.get(rec.model_name, rec.model_name)

    @api.depends("model_name", "record_id")
    def _compute_display_name_cached(self):
        """
        Busca o display_name do registro vinculado.
        Graceful degradation: se o modelo não existir, retorna label genérico.
        """
        for rec in self:
            if not rec.model_name or not rec.record_id:
                rec.display_name_cached = "—"
                continue
            try:
                model = self.env[rec.model_name]
                record = model.sudo().browse(rec.record_id)
                if record.exists():
                    rec.display_name_cached = record.display_name
                else:
                    rec.display_name_cached = f"[Registro removido] ID {rec.record_id}"
            except KeyError:
                rec.display_name_cached = f"[{rec.model_name}] ID {rec.record_id}"
            except Exception:
                rec.display_name_cached = f"[{rec.model_name}] ID {rec.record_id}"

    def action_abrir_registro(self):
        """Abre o registro vinculado na view nativa do seu modelo."""
        self.ensure_one()
        try:
            model = self.env[self.model_name]
        except KeyError:
            raise UserError(f'O módulo que gerencia "{self.model_label}" não está instalado.')
        record = model.sudo().browse(self.record_id)
        if not record.exists():
            raise UserError("O registro vinculado foi removido.")

        return {
            "type": "ir.actions.act_window",
            "res_model": self.model_name,
            "res_id": self.record_id,
            "view_mode": "form",
            "target": "current",
        }
