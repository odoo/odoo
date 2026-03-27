from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class GovAuditoriaChecklist(models.Model):
    _name = "gov.auditoria.checklist"
    _description = "Cycle Checklist"
    _order = "id desc"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    orgao_id = fields.Many2one("gov.auditoria.orgao", required=True, ondelete="restrict")
    item_ids = fields.One2many("gov.auditoria.checklist.item", "checklist_id")
    progresso = fields.Float(compute="_compute_progresso", store=False)
    item_done_count = fields.Integer(compute="_compute_counts", store=False)
    item_pending_count = fields.Integer(compute="_compute_counts", store=False)
    item_blocked_count = fields.Integer(compute="_compute_counts", store=False)

    _cycle_unique = models.Constraint(
        "unique(ciclo_id)",
        "Cada ciclo pode possuir apenas um checklist.",
    )

    @api.depends("item_ids.state")
    def _compute_progresso(self):
        for rec in self:
            total = len(rec.item_ids)
            done = len(rec.item_ids.filtered(lambda item: item.state in ("ok", "na")))
            rec.progresso = 0.0 if not total else round((done / total) * 100.0, 2)

    @api.depends("item_ids.state")
    def _compute_counts(self):
        for rec in self:
            rec.item_done_count = len(rec.item_ids.filtered(lambda item: item.state in ("ok", "na")))
            rec.item_pending_count = len(rec.item_ids.filtered(lambda item: item.state == "pendente"))
            rec.item_blocked_count = len(rec.item_ids.filtered(lambda item: item.state == "bloqueado"))

    def action_open_pending_items(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Itens Pendentes do Checklist",
            "res_model": "gov.auditoria.checklist.item",
            "view_mode": "list,form",
            "domain": [("checklist_id", "=", self.id), ("state", "in", ["pendente", "bloqueado"])],
            "context": {"default_checklist_id": self.id},
        }


class GovAuditoriaChecklistItem(models.Model):
    _name = "gov.auditoria.checklist.item"
    _description = "Cycle Checklist Item"
    _order = "sequence, id"

    checklist_id = fields.Many2one("gov.auditoria.checklist", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="checklist_id.company_id", store=True, readonly=True)
    sequence = fields.Integer(default=10)
    descricao = fields.Char(required=True)
    obrigatorio = fields.Boolean(default=True)
    state = fields.Selection(
        [
            ("pendente", "Pendente"),
            ("ok", "OK"),
            ("na", "N/A"),
            ("bloqueado", "Bloqueado"),
        ],
        default="pendente",
        required=True,
    )
    documento_id = fields.Many2one("gov.auditoria.documento", ondelete="set null")
    responsavel_id = fields.Many2one("res.users")
    observacao = fields.Text()

    def _ensure_cycle_editable(self):
        blocked_states = ("encerrado", "arquivado")
        for rec in self:
            if rec.checklist_id.ciclo_id.state in blocked_states:
                raise UserError("Nao e possivel alterar checklist de ciclos encerrados ou arquivados.")

    def _set_state(self, new_state):
        self._ensure_cycle_editable()
        for rec in self:
            if new_state == "na" and rec.obrigatorio:
                raise ValidationError("Itens obrigatorios nao podem ser marcados como N/A.")
            rec.state = new_state
        return True

    def action_mark_ok(self):
        return self._set_state("ok")

    def action_mark_na(self):
        return self._set_state("na")

    def action_mark_blocked(self):
        return self._set_state("bloqueado")

    def action_reset_state(self):
        return self._set_state("pendente")
