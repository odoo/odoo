from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovProcessoPlanilhaItem(models.Model):
    _name = "gov.processo.planilha.item"
    _description = "Item Estruturado da Planilha do Processo"
    _order = "lot_code asc, item_number asc, sequence asc, id asc"

    processo_id = fields.Many2one(
        "gov.processo",
        string="Processo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="Sequencia", default=10)
    lot_code = fields.Char(string="Lote", required=True, default="1")
    item_number = fields.Integer(string="Item", required=True, default=1)
    class_abc = fields.Selection(
        [("A", "A"), ("B", "B"), ("C", "C")],
        string="Classe ABC",
        default="C",
        required=True,
    )
    lot_description = fields.Char(string="Descricao do Lote")
    description = fields.Char(string="Descricao do Item", required=True)
    unit = fields.Char(string="Unidade", default="Un", required=True)
    monthly_quantity = fields.Float(string="Qtde./mes", digits=(16, 2))
    annual_quantity = fields.Float(string="Qtde. anual", digits=(16, 2))
    unit_price = fields.Monetary(
        string="Preco Ref. Unit.",
        currency_field="currency_id",
    )
    specification = fields.Text(string="Especificacao Tecnica Minima")
    fase = fields.Integer(string="Fase de Edicao", required=True, default=0)
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
    annual_total = fields.Monetary(
        string="Valor Anual",
        currency_field="currency_id",
        compute="_compute_totals",
        store=False,
    )
    monthly_total = fields.Monetary(
        string="Valor Mensal",
        currency_field="currency_id",
        compute="_compute_totals",
        store=False,
    )

    @api.depends("monthly_quantity", "annual_quantity", "unit_price")
    def _compute_totals(self):
        for rec in self:
            annual_quantity = rec.annual_quantity or ((rec.monthly_quantity or 0.0) * 12.0)
            rec.monthly_total = (rec.monthly_quantity or 0.0) * (rec.unit_price or 0.0)
            rec.annual_total = annual_quantity * (rec.unit_price or 0.0)

    @api.depends("fase", "processo_id.state", "processo_id.fase_atual")
    def _compute_phase_status(self):
        for rec in self:
            current_phase = rec.processo_id.fase_atual or 0
            if rec.processo_id.state == "encerrado" or current_phase > (rec.fase or 0):
                rec.status = "fechada"
                rec.can_edit = False
            elif current_phase < (rec.fase or 0):
                rec.status = "pendente"
                rec.can_edit = False
            else:
                rec.status = "aberta"
                rec.can_edit = True

    @api.onchange("monthly_quantity")
    def _onchange_monthly_quantity(self):
        for rec in self:
            if rec.monthly_quantity and not rec.annual_quantity:
                rec.annual_quantity = rec.monthly_quantity * 12.0

    @api.model
    def _ensure_phase_editable(self, processo, fase):
        processo.ensure_one()
        current_phase = processo.fase_atual or 0
        if processo.state == "encerrado" or current_phase > (fase or 0):
            raise ValidationError(
                "Os itens estruturados da planilha so podem ser alterados em fases abertas."
            )
        if current_phase < (fase or 0):
            raise ValidationError(
                "Nao e possivel cadastrar item para uma fase futura ainda nao aberta."
            )

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            processo = self.env["gov.processo"].browse(vals.get("processo_id")).exists()
            if not processo:
                raise ValidationError("Processo obrigatorio para criar item estruturado.")
            vals.setdefault("fase", processo.fase_atual or 0)
            self._ensure_phase_editable(processo, int(vals.get("fase") or 0))
            normalized_vals_list.append(vals)
        records = super().create(normalized_vals_list)
        records.mapped("processo_id").sync_planilha_structured_parameters()
        return records

    def write(self, vals):
        vals = dict(vals)
        if not self.env.context.get("skip_phase_lock"):
            target_phase = int(vals.get("fase")) if vals.get("fase") is not None else None
            for rec in self:
                fase = target_phase if target_phase is not None else (rec.fase or 0)
                self._ensure_phase_editable(rec.processo_id, fase)
        result = super().write(vals)
        self.mapped("processo_id").sync_planilha_structured_parameters()
        return result

    def unlink(self):
        if not self.env.context.get("skip_phase_lock"):
            for rec in self:
                self._ensure_phase_editable(rec.processo_id, rec.fase or 0)
        processos = self.mapped("processo_id")
        result = super().unlink()
        processos.sync_planilha_structured_parameters()
        return result

    def to_xlsx_payload_dict(self):
        self.ensure_one()
        annual_quantity = self.annual_quantity or ((self.monthly_quantity or 0.0) * 12.0)
        return {
            "lot_code": (self.lot_code or "").strip() or "1",
            "item_number": str(self.item_number or 0),
            "class_abc": self.class_abc or "",
            "lot_description": self.lot_description or "",
            "description": self.description or "",
            "unit": self.unit or "Un",
            "monthly_quantity": self.monthly_quantity or 0.0,
            "annual_quantity": annual_quantity,
            "unit_price": self.unit_price or 0.0,
            "specification": self.specification or "",
        }
