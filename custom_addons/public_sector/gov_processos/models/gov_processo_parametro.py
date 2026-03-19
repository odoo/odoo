import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .constants import DOC_TYPE_SELECTION
from .gov_template_service import GovTemplateService


class GovProcessoParametro(models.Model):
    _name = "gov.processo.parametro"
    _description = "Variável de Template do Processo"
    _order = "fase asc, sequence asc, name asc, id asc"

    _SECTION_SELECTION = [
        ("required_by_law", "Obrigatório por Lei"),
        ("optional", "Opcional"),
        ("additional_fields", "Campo Adicional"),
        ("conditional", "Condicional"),
        ("inferred", "Inferido do Template"),
    ]
    _SECTION_PRIORITY = {
        "required_by_law": 0,
        "conditional": 1,
        "optional": 2,
        "additional_fields": 3,
        "inferred": 4,
    }

    processo_id = fields.Many2one(
        "gov.processo",
        string="Processo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="Sequência", default=10)
    key = fields.Char(string="Chave", required=True, index=True)
    name = fields.Char(string="Rótulo", required=True)
    description = fields.Text(string="Descrição")
    fase = fields.Integer(string="Fase de Edição", default=0, required=True)
    doc_type = fields.Selection(DOC_TYPE_SELECTION, string="Documento de Origem")
    section = fields.Selection(
        _SECTION_SELECTION,
        string="Grupo",
        default="optional",
        required=True,
    )
    required = fields.Boolean(string="Obrigatório")
    value_type = fields.Selection(
        [
            ("string", "Texto Curto"),
            ("text", "Texto Longo"),
            ("number", "Número"),
            ("monetary", "Monetário"),
            ("date", "Data"),
            ("boolean", "Sim/Não"),
            ("json", "JSON"),
            ("array", "Lista"),
            ("object", "Objeto"),
            ("latex", "LaTeX"),
        ],
        string="Tipo",
        default="string",
        required=True,
    )
    render_mode = fields.Selection(
        [
            ("text", "Texto Seguro"),
            ("latex", "LaTeX Puro"),
        ],
        string="Modo de Renderização",
        default="text",
        required=True,
        help="Texto seguro faz escape dos caracteres especiais do LaTeX.",
    )
    value_text = fields.Text(string="Valor")
    template_ids = fields.Many2many(
        "gov.ai.template",
        "gov_processo_parametro_template_rel",
        "parametro_id",
        "template_id",
        string="Modelos Relacionados",
        copy=False,
    )
    status = fields.Selection(
        [
            ("pendente", "Fase Ainda Não Aberta"),
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
    is_filled = fields.Boolean(
        string="Preenchida",
        compute="_compute_is_filled",
        store=False,
    )
    fase_label = fields.Char(
        string="Nome da Fase",
        compute="_compute_fase_label",
        store=False,
    )

    _key_unique = models.Constraint(
        "unique(processo_id, key)",
        "Já existe uma variável com esta chave para o processo.",
    )

    @api.model
    def _normalize_key(self, key):
        return (key or "").strip()

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            vals["key"] = self._normalize_key(vals.get("key"))
            normalized_vals_list.append(vals)
        return super().create(normalized_vals_list)

    @api.depends("value_text")
    def _compute_is_filled(self):
        for rec in self:
            rec.is_filled = bool((rec.value_text or "").strip())

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

    @api.depends("fase")
    def _compute_fase_label(self):
        phase_labels = dict(self.env["gov.processo"]._fields["state"].selection)
        reverse_map = {
            0: "demanda",
            1: "instrucao",
            2: "planejamento",
            3: "licitacao",
            4: "contratacao",
            5: "execucao",
            6: "encerrado",
        }
        for rec in self:
            rec.fase_label = phase_labels.get(reverse_map.get(rec.fase), str(rec.fase or 0))

    @api.model
    def _get_section_priority(self, section):
        return self._SECTION_PRIORITY.get(section or "optional", 99)

    @api.constrains("key")
    def _check_key(self):
        for rec in self:
            key = self._normalize_key(rec.key)
            if not key:
                raise ValidationError("A chave da variável é obrigatória.")

    def write(self, vals):
        vals = dict(vals)
        if "key" in vals:
            vals["key"] = self._normalize_key(vals.get("key"))
        blocked_fields = {"value_text"}
        if not self.env.context.get("skip_phase_lock") and blocked_fields & set(vals):
            for rec in self:
                if not rec.can_edit:
                    raise ValidationError(
                        (
                            f'A variável "{rec.name}" só pode ser alterada '
                            "na fase aberta correspondente."
                        )
                    )
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get("skip_phase_lock"):
            for rec in self:
                if not rec.can_edit:
                    raise ValidationError(
                        (
                            f'A variável "{rec.name}" pertence a uma fase fechada '
                            "ou ainda não aberta e não pode ser removida."
                        )
                    )
        return super().unlink()

    def _parse_value_for_render(self):
        self.ensure_one()
        raw = (self.value_text or "").strip()
        if not raw:
            return ""

        if self.value_type in {"json", "array", "object"}:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            if isinstance(parsed, (dict, list)):
                raw = json.dumps(parsed, ensure_ascii=False)
            else:
                raw = str(parsed)

        if self.value_type == "boolean":
            normalized = raw.lower()
            if normalized in {"1", "true", "sim", "s", "yes"}:
                raw = "Sim"
            elif normalized in {"0", "false", "nao", "não", "n", "no"}:
                raw = "Não"

        if self.render_mode == "latex" or self.value_type == "latex":
            return raw
        if self.value_type == "text":
            return GovTemplateService.multiline_text_to_latex(raw)
        return GovTemplateService.escape_latex(raw)

    def to_render_pair(self):
        self.ensure_one()
        return self.key, self._parse_value_for_render()
