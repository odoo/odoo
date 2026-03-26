from odoo import api, fields, models


class GovAuditoriaChecklist(models.Model):
    _name = "gov.auditoria.checklist"
    _description = "Cycle Checklist"
    _order = "id desc"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    orgao_id = fields.Many2one("gov.auditoria.orgao", required=True, ondelete="restrict")
    item_ids = fields.One2many("gov.auditoria.checklist.item", "checklist_id")
    progresso = fields.Float(compute="_compute_progresso", store=False)

    _sql_constraints = [
        ("gov_auditoria_checklist_cycle_unique", "unique(ciclo_id)", "Cada ciclo pode possuir apenas um checklist."),
    ]

    @api.depends("item_ids.state")
    def _compute_progresso(self):
        for rec in self:
            total = len(rec.item_ids)
            done = len(rec.item_ids.filtered(lambda item: item.state in ("ok", "na")))
            rec.progresso = 0.0 if not total else round((done / total) * 100.0, 2)


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
