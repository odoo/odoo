import json
from markupsafe import Markup
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.sql import column_exists, create_column, table_exists

from .constants import PROCESS_SCOPE_SELECTION, PROCESS_TYPE_SELECTION, XLSX_PROFILE_SELECTION

class GovProcesso(models.Model):
    _name = "gov.processo"
    _description = "Processo Administrativo Governamental"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    _FASE_MAP = {
        "demanda": 0,
        "instrucao": 1,
        "planejamento": 2,
        "licitacao": 3,
        "contratacao": 4,
        "execucao": 5,
        "encerrado": 6,
    }
    _FASE_NEXT = {
        "demanda": "instrucao",
        "instrucao": "planejamento",
        "planejamento": "licitacao",
        "licitacao": "contratacao",
        "contratacao": "execucao",
        "execucao": "encerrado",
    }
    _FASE_PREV = {
        "instrucao": "demanda",
        "planejamento": "instrucao",
        "licitacao": "planejamento",
        "contratacao": "licitacao",
        "execucao": "contratacao",
        "encerrado": "execucao",
    }

    def _auto_init(self):
        result = super()._auto_init()
        if table_exists(self.env.cr, "gov_processo") and not column_exists(
            self.env.cr, "gov_processo", "xlsx_profile"
        ):
            create_column(self.env.cr, "gov_processo", "xlsx_profile", "varchar")
        self.env.cr.execute(
            """
            UPDATE gov_processo
               SET xlsx_profile = CASE
                    WHEN process_scope = 'servicos_continuados' THEN 'service_continuous_labor'
                    ELSE 'procurement_reference'
               END
             WHERE xlsx_profile IS NULL
            """
        )
        return result

    @api.model
    def _get_template_scope_values(self, scope):
        scope = scope or "compras"
        if scope == "servicos_continuados":
            return ["all", "servicos", "servicos_continuados"]
        return ["all", scope]

    @api.model
    def _default_xlsx_profile_for_scope(self, scope):
        return (
            "service_continuous_labor"
            if (scope or "compras") == "servicos_continuados"
            else "procurement_reference"
        )

    @api.model
    def _default_xlsx_profile(self):
        scope = self.env.context.get("default_process_scope") or "compras"
        return self._default_xlsx_profile_for_scope(scope)

    @api.model
    def _get_template_scope_priority(self, selected_scope, template_scope):
        if template_scope == "all":
            return 0
        if selected_scope == "servicos_continuados":
            if template_scope == "servicos":
                return 1
            if template_scope == "servicos_continuados":
                return 2
            return -1
        if template_scope == selected_scope:
            return 2
        return -1

    @api.model
    def _refine_recommended_templates(self, templates, selected_scope):
        checklists = templates.filtered("is_checklist")
        if not checklists:
            return templates

        max_priority = max(
            self._get_template_scope_priority(selected_scope, checklist.process_scope)
            for checklist in checklists
        )
        if max_priority <= 0:
            return templates

        selected_checklist_ids = set(
            checklists.filtered(
                lambda checklist: self._get_template_scope_priority(
                    selected_scope, checklist.process_scope
                )
                == max_priority
            ).ids
        )
        return templates.filtered(
            lambda template: not template.is_checklist or template.id in selected_checklist_ids
        )

    name = fields.Char(string="Número", readonly=True, copy=False, default="Novo")
    subject = fields.Char(string="Objeto / Assunto", required=True)
    ug_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
    )
    origin_type = fields.Selection(
        selection=[
            ("dfd", "DFD — Formalização de Demanda"),
            ("oficio", "Ofício / Memorando Interno"),
            ("externo", "Provocação Externa (TCE, MPE, Cidadão)"),
            ("despacho", "Despacho de Autoridade"),
            ("ne_indenizatoria", "NE Indenizatória (retroativo)"),
            ("os_urgencia", "Ordem de Serviço de Urgência"),
        ],
        string="Origem",
        required=True,
        default="dfd",
    )
    process_type = fields.Selection(
        selection=PROCESS_TYPE_SELECTION,
        string="Tipo de Processo",
        required=True,
        default="compras_servicos",
        tracking=True,
    )
    process_scope = fields.Selection(
        selection=PROCESS_SCOPE_SELECTION,
        string="Escopo",
        required=True,
        default="compras",
        tracking=True,
        help="Segregação AGU: compras, serviços ou serviços de prestação continuada.",
    )
    xlsx_profile = fields.Selection(
        selection=XLSX_PROFILE_SELECTION,
        string="Perfil XLSX",
        required=True,
        default=lambda self: self._default_xlsx_profile(),
        tracking=True,
        help="Layout principal usado pelo worker de planilhas do processo.",
    )
    state = fields.Selection(
        selection=[
            ("demanda", "Demanda"),
            ("instrucao", "Instrução"),
            ("planejamento", "Planejamento Financeiro"),
            ("licitacao", "Licitação"),
            ("contratacao", "Contratação"),
            ("execucao", "Execução Orçamentária"),
            ("encerrado", "Encerrado"),
        ],
        string="Fase",
        default="demanda",
        tracking=True,
    )
    fase_atual = fields.Integer(string="Fase (número)", compute="_compute_fase_atual", store=True)
    retroativo = fields.Boolean(string="Retroativo", default=False, tracking=True)
    urgencia = fields.Boolean(string="Urgência", default=False, tracking=True)
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsável",
        default=lambda self: self.env.user,
        tracking=True,
    )
    prazo_resposta = fields.Date(string="Prazo de Resposta")
    prazo_vencido = fields.Boolean(
        string="Prazo Vencido",
        compute="_compute_prazo_vencido",
        search="_search_prazo_vencido",
        store=False,
    )
    tramite_ids = fields.One2many(
        "gov.processo.tramite",
        "processo_id",
        string="Tramitações",
    )
    tramite_count = fields.Integer(
        string="Qtd. Tramitações",
        compute="_compute_tramite_count",
    )
    doc_ids = fields.One2many(
        "gov.processo.doc",
        "processo_id",
        string="Documentos",
    )
    doc_count = fields.Integer(
        string="Qtd. Documentos",
        compute="_compute_doc_count",
    )
    vinculo_ids = fields.One2many(
        "gov.processo.vinculo",
        "processo_id",
        string="Vínculos",
    )
    vinculo_count = fields.Integer(
        string="Qtd. Vínculos",
        compute="_compute_vinculo_count",
    )
    dotacao_ids = fields.One2many(
        "gov.processo.dotacao",
        "processo_id",
        string="Indicações Orçamentárias",
    )
    dotacao_count = fields.Integer(
        string="Dotações",
        compute="_compute_dotacao_count",
    )
    parameter_ids = fields.One2many(
        "gov.processo.parametro",
        "processo_id",
        string="Variáveis do Processo",
    )
    planilha_item_ids = fields.One2many(
        "gov.processo.planilha.item",
        "processo_id",
        string="Itens Estruturados da Planilha",
    )
    planilha_lot_ids = fields.One2many(
        "gov.processo.planilha.lote",
        "processo_id",
        string="Lotes e Cronograma XLSX",
    )
    parameter_count = fields.Integer(
        string="Variáveis",
        compute="_compute_parameter_count",
    )
    planilha_item_count = fields.Integer(
        string="Itens XLSX",
        compute="_compute_planilha_item_count",
    )
    planilha_lot_count = fields.Integer(
        string="Lotes XLSX",
        compute="_compute_planilha_lot_count",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    valor_total_estimado = fields.Monetary(
        string="Valor Total Estimado",
        currency_field="currency_id",
        compute="_compute_valor_total_estimado",
        store=True,
    )
    dotacao_indicada = fields.Boolean(
        string="Dotação Indicada",
        compute="_compute_dotacao_indicada",
        store=True,
    )
    versao_total_count = fields.Integer(
        string="Versões",
        compute="_compute_versao_total_count",
    )
    empenho_count = fields.Integer(
        string="Empenhos",
        compute="_compute_empenho_count",
    )
    recommended_template_ids = fields.Many2many(
        "gov.ai.template",
        string="Modelos Recomendados",
        compute="_compute_recommended_templates",
        compute_sudo=True,
    )
    recommended_template_count = fields.Integer(
        string="Modelos",
        compute="_compute_recommended_templates",
        compute_sudo=True,
    )

    def init(self):
        self.env.cr.execute(
            """
            UPDATE gov_processo
               SET process_scope = COALESCE(process_scope, 'compras')
             WHERE process_scope IS NULL
            """
        )

    @api.depends("state")
    def _compute_fase_atual(self):
        for rec in self:
            rec.fase_atual = self._FASE_MAP.get(rec.state, 0)

    @api.depends("tramite_ids")
    def _compute_tramite_count(self):
        for rec in self:
            rec.tramite_count = len(rec.tramite_ids)

    @api.depends("doc_ids")
    def _compute_doc_count(self):
        for rec in self:
            rec.doc_count = len(rec.doc_ids)

    @api.depends("vinculo_ids")
    def _compute_vinculo_count(self):
        for rec in self:
            rec.vinculo_count = len(rec.vinculo_ids)

    @api.depends("dotacao_ids")
    def _compute_dotacao_count(self):
        for rec in self:
            rec.dotacao_count = len(rec.dotacao_ids)

    @api.depends("parameter_ids")
    def _compute_parameter_count(self):
        for rec in self:
            rec.parameter_count = len(rec.parameter_ids)

    @api.depends("planilha_item_ids")
    def _compute_planilha_item_count(self):
        for rec in self:
            rec.planilha_item_count = len(rec.planilha_item_ids)

    @api.depends("planilha_lot_ids")
    def _compute_planilha_lot_count(self):
        for rec in self:
            rec.planilha_lot_count = len(rec.planilha_lot_ids)

    @api.depends("doc_ids.versao_ids")
    def _compute_versao_total_count(self):
        for rec in self:
            rec.versao_total_count = sum(len(doc.versao_ids) for doc in rec.doc_ids)

    def _compute_empenho_count(self):
        Empenho = self.env.get("gov.empenho")
        for rec in self:
            if Empenho is None:
                rec.empenho_count = 0
            else:
                rec.empenho_count = Empenho.search_count(
                    [
                        ("processo_id_ref", "=", rec.id),
                        ("state", "!=", "anulado"),
                    ]
                )

    @api.depends("dotacao_ids.valor_estimado")
    def _compute_valor_total_estimado(self):
        for rec in self:
            rec.valor_total_estimado = sum(d.valor_estimado for d in rec.dotacao_ids)

    @api.depends("dotacao_ids")
    def _compute_dotacao_indicada(self):
        for rec in self:
            rec.dotacao_indicada = bool(rec.dotacao_ids)

    @api.depends("process_type", "process_scope")
    def _compute_recommended_templates(self):
        Template = self.env["gov.ai.template"].sudo()
        for rec in self:
            scope = rec.process_scope or "compras"
            scope_values = self._get_template_scope_values(scope)
            templates = Template.search(
                [
                    ("active", "=", True),
                    ("process_type", "=", rec.process_type),
                    ("process_scope", "in", scope_values),
                ],
                order="is_checklist desc, process_scope, doc_type, fase, id",
            )
            templates = self._refine_recommended_templates(templates, scope)
            rec.recommended_template_ids = templates
            rec.recommended_template_count = len(templates)

    @api.onchange("process_scope")
    def _onchange_process_scope_xlsx_profile(self):
        for rec in self:
            recommended = rec._default_xlsx_profile_for_scope(rec.process_scope or "compras")
            if not rec.xlsx_profile or rec.xlsx_profile == "procurement_reference":
                rec.xlsx_profile = recommended

    @api.depends("prazo_resposta")
    def _compute_prazo_vencido(self):
        today = fields.Date.today()
        for rec in self:
            rec.prazo_vencido = bool(rec.prazo_resposta and rec.prazo_resposta < today)

    def _search_prazo_vencido(self, operator, value):
        if operator not in ("=", "!="):
            return []

        is_true = bool(value)
        today = fields.Date.today()
        overdue_domain = [("prazo_resposta", "<", today)]
        not_overdue_domain = ["|", ("prazo_resposta", "=", False), ("prazo_resposta", ">=", today)]

        if (operator == "=" and is_true) or (operator == "!=" and not is_true):
            return overdue_domain
        return not_overdue_domain

    def _set_flags_by_origin(self):
        """Define retroativo e urgencia automaticamente pela origem."""
        for rec in self:
            if rec.origin_type == "ne_indenizatoria":
                rec.retroativo = True
            if rec.origin_type == "os_urgencia":
                rec.urgencia = True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Novo") == "Novo":
                vals["name"] = self.env["ir.sequence"].next_by_code("gov.processo") or "Novo"
            vals.setdefault(
                "xlsx_profile",
                self._default_xlsx_profile_for_scope(vals.get("process_scope") or "compras"),
            )
        records = super().create(vals_list)
        for rec in records:
            rec._set_flags_by_origin()
        return records

    def action_tramitar(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Tramitar Processo",
            "res_model": "gov.processo.tramite.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_processo_id": self.id,
                "default_from_ug_id": self.env.company.id,
            },
        }

    def action_open_docs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Documentos — {self.name}",
            "res_model": "gov.processo.doc",
            "view_mode": "list,form",
            "domain": [("processo_id", "=", self.id)],
            "context": {"default_processo_id": self.id},
        }

    def action_open_vinculos(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Vínculos — {self.name}",
            "res_model": "gov.processo.vinculo",
            "view_mode": "list,form",
            "domain": [("processo_id", "=", self.id)],
            "context": {"default_processo_id": self.id},
        }

    def action_open_empenhos(self):
        self.ensure_one()
        Empenho = self.env.get("gov.empenho")
        if Empenho is None:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Modulo nao instalado",
                    "message": "Instale o modulo gov_empenho.",
                    "type": "info",
                },
            }
        return {
            "type": "ir.actions.act_window",
            "name": f"Empenhos — {self.name}",
            "res_model": "gov.empenho",
            "view_mode": "list,form",
            "domain": [("processo_id_ref", "=", self.id)],
            "context": {"default_processo_id_ref": self.id},
        }

    def action_emitir_ne(self):
        self.ensure_one()
        if self.state not in ("contratacao", "execucao"):
            raise UserError("A emissão de NE é permitida apenas nas fases Contratação ou Execução.")

        Wizard = self.env.get("gov.empenho.wizard")
        if Wizard is None:
            raise UserError(
                "Modulo gov_empenho nao instalado. "
                "Instale-o para emitir NEs diretamente do processo."
            )

        dotacao = self.dotacao_ids.filtered(lambda d: not d.reservado)[:1]
        context = {
            "default_processo_id": self.id,
            "default_objeto": self.subject or "",
            "default_retroativo": self.retroativo,
            "default_urgencia": self.urgencia,
        }
        if dotacao:
            context.update(
                {
                    "default_dotacao_id": dotacao.id,
                    "default_programa": dotacao.programa or "",
                    "default_acao": dotacao.acao or "",
                    "default_natureza_despesa": dotacao.natureza_despesa or "",
                    "default_fonte_recurso": dotacao.fonte_recurso or "",
                    "default_exercicio": dotacao.exercicio,
                    "default_valor_empenho": dotacao.valor_estimado,
                }
            )

        return {
            "type": "ir.actions.act_window",
            "name": "Emitir Nota de Empenho",
            "res_model": "gov.empenho.wizard",
            "view_mode": "form",
            "target": "new",
            "context": context,
        }

    def action_open_versoes(self):
        self.ensure_one()
        doc_ids = self.doc_ids.ids
        return {
            "type": "ir.actions.act_window",
            "name": f"Versões — {self.name}",
            "res_model": "gov.processo.versao",
            "view_mode": "list,form",
            "domain": [("doc_id", "in", doc_ids)],
        }

    def action_open_parametros(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Variáveis do Processo — {self.name}",
            "res_model": "gov.processo.parametro",
            "view_mode": "list,form",
            "domain": [("processo_id", "=", self.id)],
            "context": {
                "default_processo_id": self.id,
            },
        }

    def action_open_planilha_items(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Itens Estruturados XLSX — {self.name}",
            "res_model": "gov.processo.planilha.item",
            "view_mode": "list,form",
            "domain": [("processo_id", "=", self.id)],
            "context": {
                "default_processo_id": self.id,
                "default_fase": self.fase_atual or 0,
            },
        }

    def action_open_planilha_lots(self):
        self.ensure_one()
        self._sync_planilha_lot_records()
        return {
            "type": "ir.actions.act_window",
            "name": f"Lotes e Cronograma XLSX — {self.name}",
            "res_model": "gov.processo.planilha.lote",
            "view_mode": "list,form",
            "domain": [("processo_id", "=", self.id)],
            "context": {
                "default_processo_id": self.id,
            },
        }

    def action_sync_planilha_structured_parameters(self):
        self.ensure_one()
        self.sync_planilha_structured_parameters()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Planilha sincronizada",
                "message": "Os datasets estruturados do XLSX foram atualizados.",
                "type": "success",
            },
        }

    def action_open_modelos_recomendados(self):
        self.ensure_one()
        template_ids = self.recommended_template_ids.ids
        return {
            "type": "ir.actions.act_window",
            "name": f"Modelos e Checklists — {self.name}",
            "res_model": "gov.ai.template",
            "view_mode": "list,form",
            "domain": [("id", "in", template_ids)],
            "context": {
                "default_process_type": self.process_type,
                "default_process_scope": self.process_scope or "compras",
            },
        }

    def get_template_parameter_context(self, template=None):
        self.ensure_one()
        parameters = self.parameter_ids
        if template:
            template.ensure_one()
            keys = set(template.get_parameter_keys())
            if keys:
                parameters = parameters.filtered(lambda rec: rec.key in keys)
        context = {}
        for parameter in parameters:
            key, value = parameter.to_render_pair()
            context[key] = value
        return context

    def _serialize_planilha_item_rows(self):
        self.ensure_one()
        records = self.planilha_item_ids.sorted(
            key=lambda rec: (
                0 if (rec.lot_code or "").isdigit() else 1,
                int(rec.lot_code or 0) if (rec.lot_code or "").isdigit() else (rec.lot_code or ""),
                rec.item_number or 0,
                rec.sequence or 0,
                rec.id,
            )
        )
        return [record.to_xlsx_payload_dict() for record in records]

    def _derive_planilha_lot_rows_from_items(self):
        self.ensure_one()
        grouped = {}
        ordered_codes = []
        for item in self._serialize_planilha_item_rows():
            lot_code = item["lot_code"]
            if lot_code not in grouped:
                grouped[lot_code] = {
                    "lot_code": lot_code,
                    "description": item.get("lot_description") or item.get("description") or "",
                    "class_abc": item.get("class_abc") or "",
                    "expected_value": 0.0,
                    "notes": "",
                }
                ordered_codes.append(lot_code)
            grouped[lot_code]["expected_value"] += (item.get("annual_quantity") or 0.0) * (
                item.get("unit_price") or 0.0
            )
            if not grouped[lot_code]["description"]:
                grouped[lot_code]["description"] = item.get("description") or ""
            if not grouped[lot_code]["class_abc"]:
                grouped[lot_code]["class_abc"] = item.get("class_abc") or ""
        return [grouped[lot_code] for lot_code in ordered_codes]

    def _build_default_schedule_for_lot(self, lot_row):
        month_values = {
            month_key: ""
            for month_key in (
                "jan",
                "fev",
                "mar",
                "abr",
                "mai",
                "jun",
                "jul",
                "ago",
                "set",
                "out",
                "nov",
                "dez",
            )
        }
        class_abc = (lot_row.get("class_abc") or "").upper()
        if class_abc == "A":
            month_values.update(
                {
                    "jan": "OF 30-45 d",
                    "mar": "OF 30-45 d",
                    "mai": "OF 30-45 d",
                    "jul": "OF 45-60 d",
                    "out": "OF 30-45 d",
                    "set": "OF 45-60 d",
                    "nov": "OF 30 d",
                    "dez": "OF 30 d",
                }
            )
        elif class_abc == "B":
            month_values.update(
                {
                    "jan": "OF 30-45 d",
                    "mai": "OF 30-45 d",
                    "set": "OF 45-60 d",
                    "dez": "OF 30 d",
                }
            )
        else:
            month_values.update(
                {
                    "jan": "OF 30-45 d",
                    "jul": "OF 45-60 d",
                    "dez": "OF 30 d",
                }
            )
        return month_values

    def _sync_planilha_lot_records(self):
        Lot = self.env["gov.processo.planilha.lote"]
        for processo in self:
            derived_rows = processo._derive_planilha_lot_rows_from_items()
            existing_by_code = {
                (lot.lot_code or ""): lot
                for lot in processo.planilha_lot_ids
            }
            active_codes = []
            for row in derived_rows:
                lot_code = row["lot_code"]
                active_codes.append(lot_code)
                if lot_code in existing_by_code:
                    continue
                values = {
                    "processo_id": processo.id,
                    "lot_code": lot_code,
                    "phase": 1,
                    **processo._build_default_schedule_for_lot(row),
                }
                Lot.with_context(skip_phase_lock=True, skip_planilha_sync=True).create(values)
            orphan_rows = processo.planilha_lot_ids.filtered(
                lambda lot: (lot.lot_code or "") not in active_codes
            )
            if orphan_rows:
                orphan_rows.with_context(skip_phase_lock=True, skip_planilha_sync=True).unlink()

    def _serialize_planilha_lot_rows(self):
        self.ensure_one()
        if self.planilha_lot_ids:
            records = self.planilha_lot_ids.sorted(
                key=lambda rec: (
                    0 if (rec.lot_code or "").isdigit() else 1,
                    int(rec.lot_code or 0) if (rec.lot_code or "").isdigit() else (rec.lot_code or ""),
                    rec.id,
                )
            )
            return [record.to_lot_payload_dict() for record in records]
        return self._derive_planilha_lot_rows_from_items()

    def _serialize_planilha_schedule_rows(self):
        self.ensure_one()
        if self.planilha_lot_ids:
            records = self.planilha_lot_ids.sorted(
                key=lambda rec: (
                    0 if (rec.lot_code or "").isdigit() else 1,
                    int(rec.lot_code or 0) if (rec.lot_code or "").isdigit() else (rec.lot_code or ""),
                    rec.id,
                )
            )
            return [record.to_schedule_payload_dict() for record in records]
        rows = []
        for lot_row in self._derive_planilha_lot_rows_from_items():
            rows.append(
                {
                    "lot_code": lot_row["lot_code"],
                    "description": lot_row["description"],
                    **self._build_default_schedule_for_lot(lot_row),
                }
            )
        return rows

    def sync_planilha_structured_parameters(self):
        Parameter = self.env["gov.processo.parametro"]
        metadata_by_key = {
            "xlsx_item_rows_json": {
                "name": "[Auto] Itens estruturados da planilha XLSX",
                "description": (
                    "Gerado automaticamente a partir da grade amigavel de itens do processo."
                ),
                "fase": 0,
                "sequence": 980,
            },
            "xlsx_lot_rows_json": {
                "name": "[Auto] Resumo de lotes da planilha XLSX",
                "description": (
                    "Gerado automaticamente a partir dos itens estruturados do processo."
                ),
                "fase": 1,
                "sequence": 990,
            },
            "xlsx_schedule_rows_json": {
                "name": "[Auto] Cronograma estruturado da planilha XLSX",
                "description": (
                    "Gerado automaticamente a partir da classificacao ABC dos lotes."
                ),
                "fase": 1,
                "sequence": 1000,
            },
        }

        for processo in self:
            processo._sync_planilha_lot_records()
            payloads = {
                "xlsx_item_rows_json": processo._serialize_planilha_item_rows(),
                "xlsx_lot_rows_json": processo._serialize_planilha_lot_rows(),
                "xlsx_schedule_rows_json": processo._serialize_planilha_schedule_rows(),
            }
            existing_by_key = {rec.key: rec for rec in processo.parameter_ids}
            for key, payload in payloads.items():
                current = existing_by_key.get(key)
                value_text = json.dumps(payload, ensure_ascii=False, indent=2) if payload else ""
                metadata = metadata_by_key[key]
                values = {
                    "processo_id": processo.id,
                    "key": key,
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "fase": metadata["fase"],
                    "doc_type": "dfd",
                    "section": "additional_fields",
                    "required": False,
                    "value_type": "json",
                    "render_mode": "text",
                    "sequence": metadata["sequence"],
                    "value_text": value_text,
                }
                if current:
                    current.with_context(skip_phase_lock=True).write(values)
                elif value_text:
                    Parameter.with_context(skip_phase_lock=True).create(values)
        return True

    def _get_manual_checklist_blocks(self, mode="agu_estrito"):
        self.ensure_one()
        scope = self.process_scope or "compras"
        scope_blocks = {
            "compras": [
                "Planejamento da contratacao e definicao do objeto",
                "Pesquisa de precos e demonstracao de vantajosidade",
                "Termo de referencia e minuta contratual",
                "Adequacao orcamentaria e classificacao da despesa",
                "Publicidade, transparencia e controles",
            ],
            "servicos": [
                "Planejamento e delimitacao do escopo do servico",
                "Pesquisa de precos, composicao de custos e vantajosidade",
                "Metricas de medicao de desempenho e pagamento",
                "TR, matriz de risco e minuta contratual",
                "Fiscalizacao, sanções e controles de execucao",
            ],
            "servicos_continuados": [
                "Planejamento de servico continuado e risco de descontinuidade",
                "Pesquisa de precos e planilha de custos",
                "Obrigacoes trabalhistas, previdenciarias e fundiarias",
                "Conta vinculada, glosa e regras de fiscalizacao",
                "TR/minuta com clausulas de substituicao de pessoal e continuidade",
            ],
        }
        blocks = list(scope_blocks.get(scope, scope_blocks["compras"]))
        if self.process_type == "contratacao_direta":
            blocks.insert(0, "Fundamentacao legal da contratacao direta (art. 74/75 da Lei 14.133/21)")
            blocks.insert(1, "Justificativa motivada (emergencial, urgente ou fatica) com evidencias")
        if mode == "ug_expandido":
            blocks.extend(
                [
                    "Normas locais da UG e responsabilidades internas",
                    "Fluxo de aprovacao interna e segregacao de funcoes",
                    "Anexos complementares e evidencias adicionais",
                ]
            )
        return blocks

    def _build_manual_checklist_html(self, mode="agu_estrito"):
        self.ensure_one()
        scope_label = dict(self._fields["process_scope"].selection).get(
            self.process_scope or "compras",
            self.process_scope or "compras",
        )
        process_type_label = dict(self._fields["process_type"].selection).get(
            self.process_type,
            self.process_type,
        )
        mode_label = "AGU estrito" if mode == "agu_estrito" else "UG expandido"
        rows = []
        for block in self._get_manual_checklist_blocks(mode=mode):
            rows.append(
                "<tr style=\"background:#f6f8fa;\">"
                f"<td colspan=\"4\"><strong>{block}</strong></td>"
                "</tr>"
            )
            rows.append(
                "<tr>"
                "<td>Item obrigatorio (previsto em lei/norma)</td>"
                "<td></td><td></td><td></td>"
                "</tr>"
            )
            rows.append(
                "<tr>"
                "<td>Item opcional (com justificativa tecnica)</td>"
                "<td></td><td></td><td></td>"
                "</tr>"
            )
            if mode == "ug_expandido":
                rows.append(
                    "<tr>"
                    "<td>Campo adicional da UG (detalhamento local)</td>"
                    "<td></td><td></td><td></td>"
                    "</tr>"
                )
                rows.append(
                    "<tr>"
                    "<td>Campo adicional da UG (evidencia normativa interna)</td>"
                    "<td></td><td></td><td></td>"
                    "</tr>"
                )
            else:
                rows.append(
                    "<tr>"
                    "<td>Campo adicional da UG</td>"
                    "<td></td><td></td><td></td>"
                    "</tr>"
                )
        rows_html = "\n".join(rows)
        return """
<h3>Checklist Manual do Processo</h3>
<p><strong>Processo:</strong> {numero}</p>
<p><strong>Tipo:</strong> {tipo} | <strong>Escopo:</strong> {escopo} | <strong>Modo:</strong> {modo}</p>
<p><strong>Base:</strong> Lei 14.133/2021 (ajuste conforme regulacao local da UG).</p>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
  <thead>
    <tr>
      <th style="width:42%;">Item</th>
      <th style="width:12%;">Atende</th>
      <th style="width:22%;">Evidencia</th>
      <th style="width:24%;">Observacao</th>
    </tr>
  </thead>
  <tbody>
{rows}
  </tbody>
</table>
""".format(
            numero=self.name or "Novo",
            tipo=process_type_label,
            escopo=scope_label,
            modo=mode_label,
            rows=rows_html,
        )

    def action_novo_checklist_manual(self):
        self.ensure_one()
        checklist_mode = "agu_estrito"
        checklist_html = self._build_manual_checklist_html(mode=checklist_mode)
        scope_label = dict(self._fields["process_scope"].selection).get(
            self.process_scope or "compras",
            self.process_scope or "compras",
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Novo Checklist Manual",
            "res_model": "gov.processo.doc",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_processo_id": self.id,
                "default_doc_type": "outro",
                "default_manual_checklist": True,
                "default_checklist_mode": checklist_mode,
                "default_name": f"Checklist Manual ({scope_label}) - {self.name or 'Processo'}",
                "default_content_html": checklist_html,
            },
        }

    def action_avancar_fase(self):
        self.ensure_one()
        proximo = self._FASE_NEXT.get(self.state)
        if not proximo:
            raise UserError("O processo já está na fase final.")
        self.write({"state": proximo})
        state_label = dict(self._fields["state"].selection).get(self.state, self.state)
        self.message_post(
            body=Markup(f"<b>Fase avançada</b>: {state_label}"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_retroceder_fase(self, justificativa):
        self.ensure_one()
        if not self.env.user.has_group("gov_base.group_gov_gestor"):
            raise UserError("Apenas gestores podem retroceder fase.")
        if not justificativa or not justificativa.strip():
            raise UserError("Informe uma justificativa para retroceder a fase.")

        anterior = self._FASE_PREV.get(self.state)
        if not anterior:
            raise UserError("O processo já está na fase inicial e não pode retroceder.")

        fase_origem = dict(self._fields["state"].selection).get(self.state, self.state)
        self.write({"state": anterior})
        fase_destino = dict(self._fields["state"].selection).get(self.state, self.state)
        self.message_post(
            body=Markup(
                "<b>Fase retrocedida</b>: "
                f"{fase_origem} → {fase_destino}<br/>"
                f"<b>Justificativa</b>: {justificativa}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_abrir_wizard_avancar_fase(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Confirmar avanço de fase",
            "res_model": "gov.processo.fase.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_processo_id": self.id,
                "default_direction": "avancar",
            },
        }

    def action_abrir_wizard_retroceder_fase(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Retroceder fase",
            "res_model": "gov.processo.fase.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_processo_id": self.id,
                "default_direction": "retroceder",
            },
        }

    def action_indicar_dotacao(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Indicar Dotação Orçamentária",
            "res_model": "gov.dotacao.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_processo_id": self.id,
                "default_exercicio": fields.Date.today().year,
            },
        }

    def _criar_activity_urgencia(self):
        """
        Cria activity de regularização para processos de exceção/urgência.
        """
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return

        admin_group = self.env.ref("gov_base.group_gov_admin", raise_if_not_found=False)
        for processo in self:
            if not (processo.urgencia or processo.origin_type in ("ne_indenizatoria", "os_urgencia")):
                continue

            ja_existe = self.env["mail.activity"].search(
                [
                    ("res_model", "=", "gov.processo"),
                    ("res_id", "=", processo.id),
                    ("summary", "ilike", "Regularização"),
                ],
                limit=1,
            )
            if ja_existe:
                continue

            responsavel_id = self.env.uid
            if admin_group:
                admin_user = self.env["res.users"].search(
                    [
                        ("group_ids", "in", [admin_group.id]),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                if admin_user:
                    responsavel_id = admin_user.id

            origem_label = dict(processo._fields["origin_type"].selection).get(
                processo.origin_type,
                processo.origin_type,
            )
            processo.activity_schedule(
                activity_type_id=activity_type.id,
                summary="Regularização urgente",
                note=Markup(
                    "Processo de exceção aberto com origem "
                    f"<b>{origem_label}</b>. Verificar prazo de regularização "
                    "e documentação obrigatória."
                ),
                user_id=responsavel_id,
            )
            processo.message_post(
                body=Markup(
                    "🚨 <b>Processo de exceção</b> registrado. "
                    "Activity de regularização criada para o administrador AGI Gov."
                ),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

    def _criar_activity_prazo_externo(self):
        """
        Cria activity com deadline para processos originados por provocação externa.
        """
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return

        for processo in self:
            if processo.origin_type != "externo" or not processo.prazo_resposta:
                continue

            ja_existe = self.env["mail.activity"].search(
                [
                    ("res_model", "=", "gov.processo"),
                    ("res_id", "=", processo.id),
                    ("summary", "ilike", "Resposta a provocação"),
                ],
                limit=1,
            )
            if ja_existe:
                continue

            processo.activity_schedule(
                activity_type_id=activity_type.id,
                summary="Resposta a provocação externa",
                note=Markup(
                    "Prazo de resposta: "
                    f"<b>{processo.prazo_resposta.strftime('%d/%m/%Y')}</b>. "
                    "Providenciar resposta formal ao demandante externo."
                ),
                date_deadline=processo.prazo_resposta,
                user_id=processo.responsible_id.id or self.env.uid,
            )

    @api.model
    def _cron_alertar_prazos(self):
        """
        Execução diária. Verifica processos com prazo_resposta vencendo
        em até 7 dias ou já vencidos.
        """
        hoje = fields.Date.today()
        alerta_ate = hoje + relativedelta(days=7)

        proximos = self.search(
            [
                ("prazo_resposta", ">=", hoje),
                ("prazo_resposta", "<=", alerta_ate),
                ("state", "not in", ["encerrado"]),
            ]
        )
        for processo in proximos:
            dias = (processo.prazo_resposta - hoje).days
            processo.message_post(
                body=Markup(
                    f"⏰ <b>Alerta de prazo:</b> este processo vence em "
                    f"<b>{dias} dia(s)</b> "
                    f"({processo.prazo_resposta.strftime('%d/%m/%Y')})."
                ),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

        vencidos = self.search(
            [
                ("prazo_resposta", "<", hoje),
                ("state", "not in", ["encerrado"]),
            ]
        )
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        for processo in vencidos:
            activity_existente = self.env["mail.activity"].search(
                [
                    ("res_model", "=", "gov.processo"),
                    ("res_id", "=", processo.id),
                    ("summary", "=", "Prazo vencido"),
                ],
                limit=1,
            )
            if not activity_existente and activity_type:
                processo.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary="Prazo vencido",
                    note=Markup(
                        f"O prazo de resposta venceu em "
                        f"{processo.prazo_resposta.strftime('%d/%m/%Y')}. "
                        f"Providências necessárias."
                    ),
                    user_id=processo.responsible_id.id or self.env.uid,
                )
            processo.message_post(
                body=Markup(
                    f"🚨 <b>PRAZO VENCIDO</b> em "
                    f"{processo.prazo_resposta.strftime('%d/%m/%Y')}. "
                    f"Providências necessárias."
                ),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

    @api.model
    def _cron_alertar_inercia(self):
        """
        Execução diária. Verifica processos em andamento sem tramitação
        nos últimos 21 dias corridos (aproximação de 15 dias úteis).
        """
        limite = fields.Datetime.now() - relativedelta(days=21)
        estados_ativos = [
            "instrucao",
            "planejamento",
            "licitacao",
            "contratacao",
            "execucao",
        ]

        processos_ativos = self.search([("state", "in", estados_ativos)])
        inicio_hoje = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for processo in processos_ativos:
            ultimo_tramite = self.env["gov.processo.tramite"].search(
                [("processo_id", "=", processo.id)],
                order="date desc",
                limit=1,
            )

            sem_movimento = not ultimo_tramite or ultimo_tramite.date < limite
            if not sem_movimento:
                continue

            ja_alertado = self.env["mail.message"].search(
                [
                    ("res_id", "=", processo.id),
                    ("model", "=", "gov.processo"),
                    ("body", "ilike", "sem movimentação"),
                    ("date", ">=", inicio_hoje),
                ],
                limit=1,
            )
            if ja_alertado:
                continue

            data_ultimo = ultimo_tramite.date.strftime("%d/%m/%Y") if ultimo_tramite else "nenhuma"
            processo.message_post(
                body=Markup(
                    f"🔔 <b>Processo sem movimentação</b> há mais de 21 dias. "
                    f"Última tramitação: {data_ultimo}. "
                    f"Verifique o andamento."
                ),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
                partner_ids=processo.responsible_id.mapped("partner_id").ids,
            )

    @api.model
    def _criar_vinculo(self, processo_id, model_name, record_id, vinculo_type="instrui"):
        """
        Helper para uso por outros addons.
        Evita duplicação: não cria se já existir o mesmo vínculo.
        """
        Vinculo = self.env["gov.processo.vinculo"]
        existente = Vinculo.search(
            [
                ("processo_id", "=", processo_id),
                ("model_name", "=", model_name),
                ("record_id", "=", record_id),
                ("vinculo_type", "=", vinculo_type),
            ],
            limit=1,
        )
        if not existente:
            return Vinculo.create(
                {
                    "processo_id": processo_id,
                    "model_name": model_name,
                    "record_id": record_id,
                    "vinculo_type": vinculo_type,
                }
            )
        return existente
