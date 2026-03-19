from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovProcessoPlanilhaLote(models.Model):
    _name = "gov.processo.planilha.lote"
    _description = "Lote Estruturado da Planilha do Processo"
    _order = "lot_code asc, id asc"

    processo_id = fields.Many2one(
        "gov.processo",
        string="Processo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    lot_code = fields.Char(string="Lote", required=True)
    phase = fields.Integer(string="Fase de Edicao", required=True, default=1)
    description_override = fields.Char(string="Descricao Manual do Lote")
    class_abc_override = fields.Selection(
        [("A", "A"), ("B", "B"), ("C", "C")],
        string="Classe ABC Manual",
    )
    notes = fields.Text(string="Observacoes")
    jan = fields.Char(string="Jan")
    fev = fields.Char(string="Fev")
    mar = fields.Char(string="Mar")
    abr = fields.Char(string="Abr")
    mai = fields.Char(string="Mai")
    jun = fields.Char(string="Jun")
    jul = fields.Char(string="Jul")
    ago = fields.Char(string="Ago")
    set = fields.Char(string="Set")
    out = fields.Char(string="Out")
    nov = fields.Char(string="Nov")
    dez = fields.Char(string="Dez")
    currency_id = fields.Many2one(
        related="processo_id.currency_id",
        readonly=True,
        store=False,
    )
    status = fields.Selection(
        [
            ("pendente", "Fase Ainda Nao Aberta"),
            ("aberta", "Fase Aberta"),
            ("fechada", "Fase Encerrada"),
        ],
        string="Status",
        compute="_compute_phase_status",
        store=False,
    )
    can_edit = fields.Boolean(
        string="Pode Editar",
        compute="_compute_phase_status",
        store=False,
    )
    item_count = fields.Integer(
        string="Qtd. Itens",
        compute="_compute_derived_values",
        store=False,
    )
    expected_value = fields.Monetary(
        string="Valor Estimado",
        currency_field="currency_id",
        compute="_compute_derived_values",
        store=False,
    )
    description_effective = fields.Char(
        string="Descricao Efetiva",
        compute="_compute_derived_values",
        store=False,
    )
    class_abc_effective = fields.Char(
        string="Classe Efetiva",
        compute="_compute_derived_values",
        store=False,
    )

    _lot_code_unique = models.Constraint(
        "unique(processo_id, lot_code)",
        "Ja existe um lote estruturado com este codigo para o processo.",
    )

    @api.depends("phase", "processo_id.state", "processo_id.fase_atual")
    def _compute_phase_status(self):
        for rec in self:
            current_phase = rec.processo_id.fase_atual or 0
            if rec.processo_id.state == "encerrado" or current_phase > (rec.phase or 0):
                rec.status = "fechada"
                rec.can_edit = False
            elif current_phase < (rec.phase or 0):
                rec.status = "pendente"
                rec.can_edit = False
            else:
                rec.status = "aberta"
                rec.can_edit = True

    @api.depends(
        "description_override",
        "class_abc_override",
        "processo_id.planilha_item_ids",
        "processo_id.planilha_item_ids.lot_code",
        "processo_id.planilha_item_ids.lot_description",
        "processo_id.planilha_item_ids.description",
        "processo_id.planilha_item_ids.class_abc",
        "processo_id.planilha_item_ids.annual_total",
    )
    def _compute_derived_values(self):
        for rec in self:
            related_items = rec.processo_id.planilha_item_ids.filtered(
                lambda item: (item.lot_code or "") == (rec.lot_code or "")
            )
            rec.item_count = len(related_items)
            rec.expected_value = sum(item.annual_total for item in related_items)
            rec.description_effective = (
                rec.description_override
                or next(
                    (
                        item.lot_description or item.description
                        for item in related_items
                        if item.lot_description or item.description
                    ),
                    "",
                )
            )
            rec.class_abc_effective = (
                rec.class_abc_override
                or next((item.class_abc for item in related_items if item.class_abc), "")
            )

    @api.model
    def _ensure_phase_editable(self, processo, phase):
        processo.ensure_one()
        current_phase = processo.fase_atual or 0
        if processo.state == "encerrado" or current_phase > (phase or 0):
            raise ValidationError(
                "Os lotes estruturados do XLSX so podem ser alterados em fases abertas."
            )
        if current_phase < (phase or 0):
            raise ValidationError(
                "Nao e possivel alterar um lote de fase futura ainda nao aberta."
            )

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            processo = self.env["gov.processo"].browse(vals.get("processo_id")).exists()
            if not processo:
                raise ValidationError("Processo obrigatorio para criar lote estruturado.")
            vals.setdefault("phase", 1)
            if not self.env.context.get("skip_phase_lock"):
                self._ensure_phase_editable(processo, int(vals.get("phase") or 1))
            normalized_vals_list.append(vals)
        records = super().create(normalized_vals_list)
        if not self.env.context.get("skip_planilha_sync"):
            records.mapped("processo_id").sync_planilha_structured_parameters()
        return records

    def write(self, vals):
        vals = dict(vals)
        if not self.env.context.get("skip_phase_lock"):
            target_phase = int(vals.get("phase")) if vals.get("phase") is not None else None
            for rec in self:
                phase = target_phase if target_phase is not None else (rec.phase or 1)
                self._ensure_phase_editable(rec.processo_id, phase)
        result = super().write(vals)
        if not self.env.context.get("skip_planilha_sync"):
            self.mapped("processo_id").sync_planilha_structured_parameters()
        return result

    def unlink(self):
        if not self.env.context.get("skip_phase_lock"):
            for rec in self:
                self._ensure_phase_editable(rec.processo_id, rec.phase or 1)
        processos = self.mapped("processo_id")
        result = super().unlink()
        if not self.env.context.get("skip_planilha_sync"):
            processos.sync_planilha_structured_parameters()
        return result

    def to_lot_payload_dict(self):
        self.ensure_one()
        return {
            "lot_code": self.lot_code or "",
            "description": self.description_effective or "",
            "class_abc": self.class_abc_effective or "",
            "expected_value": self.expected_value or 0.0,
            "notes": self.notes or "",
        }

    def to_schedule_payload_dict(self):
        self.ensure_one()
        return {
            "lot_code": self.lot_code or "",
            "description": self.description_effective or "",
            "jan": self.jan or "",
            "fev": self.fev or "",
            "mar": self.mar or "",
            "abr": self.abr or "",
            "mai": self.mai or "",
            "jun": self.jun or "",
            "jul": self.jul or "",
            "ago": self.ago or "",
            "set": self.set or "",
            "out": self.out or "",
            "nov": self.nov or "",
            "dez": self.dez or "",
        }
