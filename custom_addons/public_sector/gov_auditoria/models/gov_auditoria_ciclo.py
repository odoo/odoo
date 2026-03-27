import base64
import hashlib
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.gov_processos.models.gov_typst_service import GovTypstService


class GovAuditoriaCiclo(models.Model):
    _name = "gov.auditoria.ciclo"
    _description = "Annual Accountability Cycle"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "exercicio_id desc, company_id, id desc"

    _STATE_SELECTION = [
        ("rascunho", "Rascunho"),
        ("consolidacao", "Consolidacao"),
        ("conferencia", "Conferencia"),
        ("remessa", "Remessa"),
        ("em_analise", "Em Analise"),
        ("diligencia", "Diligencia"),
        ("defesa", "Defesa"),
        ("julgamento", "Julgamento"),
        ("acordao", "Acordao"),
        ("recurso", "Recurso"),
        ("cumprimento", "Cumprimento"),
        ("encerrado", "Encerrado"),
        ("arquivado", "Arquivado"),
    ]

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, readonly=True)
    exercicio_id = fields.Many2one(
        "account.fiscal.year",
        required=True,
        tracking=True,
        domain="[('company_id', '=', company_id)]",
        ondelete="restrict",
    )
    orgao_id = fields.Many2one(
        "gov.auditoria.orgao",
        required=True,
        tracking=True,
        ondelete="restrict",
    )
    tipo_prestacao = fields.Selection(
        [
            ("ordinaria", "Ordinaria"),
            ("especial", "Especial"),
            ("tomada_de_contas_especial", "Tomada de Contas Especial"),
        ],
        required=True,
        default="ordinaria",
        tracking=True,
    )
    modo_dados = fields.Selection(
        [
            ("nativo", "Nativo"),
            ("espelho", "Espelho"),
            ("hibrido", "Hibrido"),
        ],
        required=True,
        default="nativo",
        tracking=True,
    )
    state = fields.Selection(_STATE_SELECTION, required=True, default="rascunho", tracking=True)
    processo_id = fields.Many2one("gov.processo", ondelete="set null")
    responsavel_ids = fields.Many2many("res.users", string="Responsaveis")
    auditor_externo_ids = fields.Many2many(
        "res.users",
        "gov_auditoria_ciclo_auditor_rel",
        "ciclo_id",
        "user_id",
        string="Auditores Externos",
    )
    data_abertura = fields.Date(default=fields.Date.today)
    data_remessa = fields.Date()
    data_encerramento = fields.Date()
    numero_protocolo = fields.Char()
    evento_ids = fields.One2many("gov.auditoria.evento", "ciclo_id")
    prazo_ids = fields.One2many("gov.auditoria.prazo", "ciclo_id")
    documento_ids = fields.One2many("gov.auditoria.documento", "ciclo_id")
    apontamento_ids = fields.One2many("gov.auditoria.apontamento", "ciclo_id")
    decisao_id = fields.Many2one("gov.auditoria.decisao", ondelete="set null")
    checklist_id = fields.Many2one("gov.auditoria.checklist", ondelete="set null", copy=False)
    checklist_progresso = fields.Float(related="checklist_id.progresso", readonly=True)
    checklist_pendente_count = fields.Integer(related="checklist_id.item_pending_count", readonly=True)
    checklist_bloqueado_count = fields.Integer(related="checklist_id.item_blocked_count", readonly=True)
    espelho_ids = fields.One2many("gov.auditoria.espelho", "ciclo_id")
    doc_processo_ref_ids = fields.Many2many(
        "gov.processo.doc",
        "gov_auditoria_ciclo_processo_doc_rel",
        "ciclo_id",
        "doc_id",
        string="Docs do Processo",
        readonly=True,
    )
    nota_interna = fields.Text()
    mapeamento_validado = fields.Boolean(
        string="Mapeamento Contabil Validado",
        default=False,
        help="Required for annual reporting in native mode.",
    )
    cobertura_espelho_pct = fields.Float(
        string="Cobertura do Espelho (%)",
        compute="_compute_cobertura_espelho_pct",
        store=False,
    )
    reporting_ready = fields.Boolean(
        string="Apto para Reporte",
        compute="_compute_reporting_ready",
        store=False,
    )
    situacao_executiva = fields.Selection(
        [
            ("critica", "Critica"),
            ("atencao", "Atencao"),
            ("controlada", "Controlada"),
        ],
        compute="_compute_situacao_executiva",
        store=False,
    )
    proximo_vencimento = fields.Date(compute="_compute_deadline_metrics", store=False)
    prazo_vigente_count = fields.Integer(compute="_compute_deadline_metrics", store=False)
    prazo_vencido_count = fields.Integer(compute="_compute_deadline_metrics", store=False)
    documento_enviado_count = fields.Integer(compute="_compute_document_metrics", store=False)
    documento_pendente_count = fields.Integer(compute="_compute_document_metrics", store=False)
    apontamento_aberto_count = fields.Integer(compute="_compute_apontamento_metrics", store=False)
    determinacao_pendente_count = fields.Integer(compute="_compute_determinacao_metrics", store=False)
    ultimo_evento_em = fields.Datetime(compute="_compute_event_metrics", store=False)
    has_prazo_vencido = fields.Boolean(compute="_compute_dashboard_flags", store=True)
    has_documento_pendente = fields.Boolean(compute="_compute_dashboard_flags", store=True)
    has_apontamento_aberto = fields.Boolean(compute="_compute_dashboard_flags", store=True)
    has_determinacao_pendente = fields.Boolean(compute="_compute_dashboard_flags", store=True)
    has_pendencia_critica = fields.Boolean(compute="_compute_dashboard_flags", store=True)
    has_pendencia_operacional = fields.Boolean(compute="_compute_dashboard_flags", store=True)
    native_empenho_count = fields.Integer(compute="_compute_native_counts", store=False)
    native_liquidacao_count = fields.Integer(compute="_compute_native_counts", store=False)
    native_pagamento_count = fields.Integer(compute="_compute_native_counts", store=False)

    _cycle_unique = models.Constraint(
        "unique(company_id, exercicio_id, orgao_id, tipo_prestacao)",
        "Ja existe um ciclo para a mesma UG, exercicio, orgao e tipo de prestacao.",
    )

    @api.depends("company_id", "exercicio_id", "orgao_id")
    def _compute_name(self):
        for rec in self:
            year_name = rec.exercicio_id.name or rec.exercicio_id.date_to or ""
            company = rec.company_id.display_name or ""
            orgao = rec.orgao_id.sigla or rec.orgao_id.name or ""
            rec.name = f"Prestacao {year_name} - {company} - {orgao}".strip(" -")

    @api.depends("espelho_ids.valor", "espelho_ids.validado")
    def _compute_cobertura_espelho_pct(self):
        for rec in self:
            total = sum(abs(item.valor or 0.0) for item in rec.espelho_ids)
            validated = sum(abs(item.valor or 0.0) for item in rec.espelho_ids.filtered("validado"))
            rec.cobertura_espelho_pct = 0.0 if not total else round((validated / total) * 100.0, 2)

    @api.depends(
        "modo_dados",
        "mapeamento_validado",
        "cobertura_espelho_pct",
        "company_id",
        "exercicio_id",
    )
    def _compute_reporting_ready(self):
        for rec in self:
            fiscal_ready = bool(rec.exercicio_id and rec.exercicio_id.is_gov_reporting_ready())
            if rec.modo_dados == "espelho":
                rec.reporting_ready = rec.cobertura_espelho_pct >= 100.0
            elif rec.modo_dados == "hibrido":
                rec.reporting_ready = bool(fiscal_ready and rec.mapeamento_validado and rec.cobertura_espelho_pct >= 100.0)
            else:
                rec.reporting_ready = bool(fiscal_ready and rec.mapeamento_validado)

    @api.depends("prazo_ids.state", "prazo_ids.data_fim_real", "prazo_ids.data_fim_legal")
    def _compute_deadline_metrics(self):
        today = fields.Date.today()
        for rec in self:
            relevant_deadlines = rec.prazo_ids.filtered(lambda prazo: prazo.state not in ("cumprido", "cancelado"))
            rec.prazo_vigente_count = len(relevant_deadlines.filtered(lambda prazo: prazo.state == "vigente"))
            rec.prazo_vencido_count = len(relevant_deadlines.filtered(lambda prazo: prazo.state == "vencido"))
            ordered = sorted(
                relevant_deadlines,
                key=lambda prazo: prazo.data_fim_real or prazo.data_fim_legal or today,
            )
            rec.proximo_vencimento = ordered[0].data_fim_real or ordered[0].data_fim_legal if ordered else False

    @api.depends("documento_ids.state")
    def _compute_document_metrics(self):
        for rec in self:
            rec.documento_enviado_count = len(rec.documento_ids.filtered(lambda doc: doc.state == "enviado"))
            rec.documento_pendente_count = len(rec.documento_ids.filtered(lambda doc: doc.state in ("rascunho", "finalizado")))

    @api.depends("apontamento_ids.state")
    def _compute_apontamento_metrics(self):
        for rec in self:
            rec.apontamento_aberto_count = len(
                rec.apontamento_ids.filtered(lambda item: item.state in ("aberto", "respondido"))
            )

    @api.depends("decisao_id.determination_ids.state")
    def _compute_determinacao_metrics(self):
        for rec in self:
            determinacoes = rec.decisao_id.determination_ids.filtered(
                lambda item: item.state in ("pendente", "parcial", "descumprido")
            )
            rec.determinacao_pendente_count = len(determinacoes)

    @api.depends("evento_ids.data_evento")
    def _compute_event_metrics(self):
        for rec in self:
            rec.ultimo_evento_em = max(rec.evento_ids.mapped("data_evento"), default=False)

    @api.depends(
        "prazo_ids.state",
        "documento_ids.state",
        "apontamento_ids.state",
        "decisao_id.determination_ids.state",
    )
    def _compute_dashboard_flags(self):
        for rec in self:
            rec.has_prazo_vencido = bool(rec.prazo_ids.filtered(lambda item: item.state == "vencido"))
            rec.has_documento_pendente = bool(
                rec.documento_ids.filtered(lambda item: item.state in ("rascunho", "finalizado"))
            )
            rec.has_apontamento_aberto = bool(
                rec.apontamento_ids.filtered(lambda item: item.state in ("aberto", "respondido"))
            )
            rec.has_determinacao_pendente = bool(
                rec.decisao_id.determination_ids.filtered(lambda item: item.state in ("pendente", "parcial", "descumprido"))
            )
            rec.has_pendencia_critica = bool(rec.has_prazo_vencido or rec.has_determinacao_pendente)
            rec.has_pendencia_operacional = bool(
                rec.has_pendencia_critica or rec.has_documento_pendente or rec.has_apontamento_aberto
            )

    @api.depends(
        "prazo_vencido_count",
        "apontamento_aberto_count",
        "reporting_ready",
        "state",
        "proximo_vencimento",
    )
    def _compute_situacao_executiva(self):
        today = fields.Date.today()
        for rec in self:
            if rec.prazo_vencido_count or rec.state in ("diligencia", "recurso"):
                rec.situacao_executiva = "critica"
            elif rec.apontamento_aberto_count or (rec.proximo_vencimento and rec.proximo_vencimento <= today + timedelta(days=5)):
                rec.situacao_executiva = "atencao"
            else:
                rec.situacao_executiva = "controlada"

    @api.depends("company_id", "exercicio_id")
    def _compute_native_counts(self):
        Empenho = self.env["gov.empenho"]
        Liquidacao = self.env["gov.liquidacao"]
        Pagamento = self.env["gov.pagamento"]
        for rec in self:
            if not rec.company_id or not rec.exercicio_id:
                rec.native_empenho_count = 0
                rec.native_liquidacao_count = 0
                rec.native_pagamento_count = 0
                continue
            exercise = rec._get_exercicio_label()
            domain = [("ug_id", "=", rec.company_id.id), ("exercicio", "=", exercise)]
            rec.native_empenho_count = Empenho.search_count(domain)
            rec.native_liquidacao_count = Liquidacao.search_count(domain)
            rec.native_pagamento_count = Pagamento.search_count(domain)

    def _get_exercicio_label(self):
        self.ensure_one()
        if not self.exercicio_id:
            return False
        return self.exercicio_id.date_to.year if self.exercicio_id.date_to else False

    def _ensure_manager(self):
        if not self.env.user.has_group("gov_auditoria.group_auditoria_manager") and not self.env.user.has_group(
            "gov_auditoria.group_auditoria_admin"
        ):
            raise UserError("Voce nao possui permissao para avancar o ciclo.")

    def _get_activity_owner_id(self):
        self.ensure_one()
        return (self.responsavel_ids[:1].id or self.create_uid.id or self.env.uid)

    def _sync_activity_flag(self, summary, note, active, deadline=False):
        self.ensure_one()
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return
        existing = self.env["mail.activity"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("summary", "=", summary),
            ]
        )
        if not active:
            if existing:
                existing.unlink()
            return
        vals = {
            "activity_type_id": activity_type.id,
            "summary": summary,
            "note": note,
            "user_id": self._get_activity_owner_id(),
        }
        if deadline:
            vals["date_deadline"] = deadline
        if existing:
            existing.write(vals)
        else:
            self.activity_schedule(**vals)

    def _sync_operational_activities(self):
        today = fields.Date.today()
        for rec in self:
            due_soon_deadlines = rec.prazo_ids.filtered(
                lambda item: item.state == "vigente" and (item.data_fim_real or item.data_fim_legal) and (item.data_fim_real or item.data_fim_legal) <= today + timedelta(days=5)
            )
            next_due = min((item.data_fim_real or item.data_fim_legal for item in due_soon_deadlines), default=False)
            rec._sync_activity_flag(
                summary="Prazo proximo",
                note="Ha prazo do ciclo vencendo em ate 5 dias.",
                active=bool(due_soon_deadlines),
                deadline=next_due,
            )
            overdue = rec.prazo_ids.filtered(lambda item: item.state == "vencido")
            overdue_date = min((item.data_fim_real or item.data_fim_legal for item in overdue), default=False)
            rec._sync_activity_flag(
                summary="Prazo vencido",
                note="Ha prazo vencido no ciclo de auditoria. Priorizar regularizacao.",
                active=bool(overdue),
                deadline=overdue_date,
            )
            pending_docs = rec.documento_ids.filtered(lambda item: item.state in ("rascunho", "finalizado"))
            rec._sync_activity_flag(
                summary="Documento pendente",
                note="Existem documentos pendentes de envio ou finalizacao no ciclo.",
                active=bool(pending_docs),
            )
            pending_determinations = rec.decisao_id.determination_ids.filtered(
                lambda item: item.state in ("pendente", "parcial", "descumprido")
            )
            determination_deadline = min((item.prazo_cumprimento for item in pending_determinations if item.prazo_cumprimento), default=False)
            rec._sync_activity_flag(
                summary="Cumprimento pendente",
                note="Existem determinacoes sem comprovacao de cumprimento.",
                active=bool(pending_determinations),
                deadline=determination_deadline,
            )

    @api.model
    def _cron_sync_operational_activities(self):
        cycles = self.search([("state", "not in", ["encerrado", "arquivado"])])
        cycles._sync_operational_activities()

    def write(self, vals):
        if not self.env.user.has_group("gov_auditoria.group_auditoria_admin"):
            locked_cycles = self.filtered(lambda rec: rec.state in ("encerrado", "arquivado"))
            if locked_cycles:
                raise UserError("Ciclos encerrados ou arquivados sao somente leitura para este perfil.")
        result = super().write(vals)
        self._sync_operational_activities()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_operational_activities()
        return records

    def _set_state(self, new_state):
        self.ensure_one()
        self._ensure_manager()
        vals = {"state": new_state}
        if new_state == "remessa" and not self.data_remessa:
            vals["data_remessa"] = fields.Date.today()
        if new_state in ("encerrado", "arquivado") and not self.data_encerramento:
            vals["data_encerramento"] = fields.Date.today()
        self.write(vals)
        return True

    def action_to_consolidacao(self):
        for rec in self:
            rec._set_state("consolidacao")
        return True

    def action_to_conferencia(self):
        for rec in self:
            rec._set_state("conferencia")
        return True

    def action_to_remessa(self):
        for rec in self:
            if not rec.reporting_ready:
                raise UserError("O ciclo ainda nao esta apto para remessa.")
            rec._set_state("remessa")
            rec._ensure_checklist()
            rec._ensure_default_deadlines()
        return True

    def action_to_em_analise(self):
        for rec in self:
            rec._set_state("em_analise")
        return True

    def action_to_diligencia(self):
        for rec in self:
            rec._set_state("diligencia")
            rec._create_event_with_deadline(
                tipo="diligencia_emitida",
                descricao="Diligencia registrada no ciclo.",
                prazo_dias=rec.orgao_id.prazo_defesa_dias,
                prazo_tipo="legal",
            )
        return True

    def action_to_defesa(self):
        for rec in self:
            rec._set_state("defesa")
        return True

    def action_to_julgamento(self):
        for rec in self:
            rec._set_state("julgamento")
        return True

    def action_to_acordao(self):
        for rec in self:
            rec._set_state("acordao")
        return True

    def action_open_diligencia_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Registrar Diligencia",
            "res_model": "gov.auditoria.diligencia.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_ciclo_id": self.id},
        }

    def action_open_checklist(self):
        self.ensure_one()
        checklist = self._ensure_checklist()
        return {
            "type": "ir.actions.act_window",
            "name": "Checklist do Ciclo",
            "res_model": "gov.auditoria.checklist",
            "res_id": checklist.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_acordao_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Registrar Acordao",
            "res_model": "gov.auditoria.acordao.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_ciclo_id": self.id},
        }

    def action_open_protocolo_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Registrar Protocolo de Envio",
            "res_model": "gov.auditoria.protocolo.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_ciclo_id": self.id},
        }

    def action_generate_diligencia_typst(self):
        for rec in self:
            rec._generate_diligencia_document()
        return True

    def action_generate_dossier_typst(self):
        for rec in self:
            rec._generate_dossier_document()
        return True

    def action_open_overdue_deadlines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Prazos Vencidos",
            "res_model": "gov.auditoria.prazo",
            "view_mode": "list,form",
            "domain": [("ciclo_id", "=", self.id), ("state", "=", "vencido")],
            "context": {"default_ciclo_id": self.id},
        }

    def action_open_pending_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Documentos Pendentes",
            "res_model": "gov.auditoria.documento",
            "view_mode": "list,form",
            "domain": [("ciclo_id", "=", self.id), ("state", "in", ["rascunho", "finalizado"])],
            "context": {"default_ciclo_id": self.id},
        }

    def action_open_open_findings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Apontamentos Abertos",
            "res_model": "gov.auditoria.apontamento",
            "view_mode": "list,form",
            "domain": [("ciclo_id", "=", self.id), ("state", "in", ["aberto", "respondido"])],
            "context": {"default_ciclo_id": self.id},
        }

    def action_open_pending_determinations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Determinacoes Pendentes",
            "res_model": "gov.auditoria.determinacao",
            "view_mode": "list,form",
            "domain": [("decisao_id", "=", self.decisao_id.id), ("state", "in", ["pendente", "parcial", "descumprido"])],
            "context": {"default_decisao_id": self.decisao_id.id},
        }

    def action_to_recurso(self):
        for rec in self:
            rec._set_state("recurso")
            rec._create_event_with_deadline(
                tipo="recurso_interposto",
                descricao="Prazo recursal iniciado.",
                prazo_dias=rec.orgao_id.prazo_recurso_dias,
                prazo_tipo="legal",
            )
        return True

    def action_to_cumprimento(self):
        for rec in self:
            rec._set_state("cumprimento")
        return True

    def action_to_encerrado(self):
        for rec in self:
            rec._set_state("encerrado")
        return True

    def action_to_arquivado(self):
        for rec in self:
            rec._set_state("arquivado")
        return True

    def _ensure_checklist(self):
        self.ensure_one()
        if self.checklist_id:
            return self.checklist_id
        checklist = self.env["gov.auditoria.checklist"].create(
            {
                "ciclo_id": self.id,
                "orgao_id": self.orgao_id.id,
            }
        )
        template = self.orgao_id.checklist_template_ids[:1]
        if template:
            for item in template.item_ids:
                self.env["gov.auditoria.checklist.item"].create(
                    {
                        "checklist_id": checklist.id,
                        "descricao": item.descricao,
                        "obrigatorio": item.obrigatorio,
                    }
                )
        self.checklist_id = checklist.id
        return checklist

    def _ensure_default_deadlines(self):
        self.ensure_one()
        if self.prazo_ids.filtered(lambda prazo: prazo.tipo == "legal" and prazo.descricao == "Prazo padrao de remessa"):
            return
        base_date = self.data_remessa or fields.Date.today()
        end_date = base_date + timedelta(days=self.orgao_id.prazo_remessa_dias or 0)
        self.env["gov.auditoria.prazo"].create(
            {
                "ciclo_id": self.id,
                "tipo": "legal",
                "descricao": "Prazo padrao de remessa",
                "data_inicio": base_date,
                "data_fim_legal": end_date,
                "dias": self.orgao_id.prazo_remessa_dias or 0,
                "alerta_antecedencia_dias": 5,
            }
        )

    def _create_event_with_deadline(self, tipo, descricao, prazo_dias=0, prazo_tipo="legal"):
        self.ensure_one()
        event = self.env["gov.auditoria.evento"].create(
            {
                "ciclo_id": self.id,
                "tipo": tipo,
                "descricao": descricao,
                "data_evento": fields.Datetime.now(),
                "responsavel_id": self.env.user.id,
                "origem": "manual",
            }
        )
        if prazo_dias:
            start_date = fields.Date.today()
            self.env["gov.auditoria.prazo"].create(
                {
                    "ciclo_id": self.id,
                    "evento_id": event.id,
                    "tipo": prazo_tipo,
                    "descricao": descricao,
                    "data_inicio": start_date,
                    "data_fim_legal": start_date + timedelta(days=prazo_dias),
                    "dias": prazo_dias,
                    "alerta_antecedencia_dias": 3,
                }
            )
        return event

    def _selection_label(self, field_name, value):
        selection = dict(self._fields[field_name].selection)
        return selection.get(value, value or "-")

    def _render_typst_document(self, bindings, body, *, title, eyebrow, subtitle):
        from odoo.addons.gov_processos.services.gov_typst_serializer import GovTypstSerializer

        theme = r"""
#set page(
  paper: "a4",
  margin: (top: 1.55cm, bottom: 1.6cm, left: 1.8cm, right: 1.8cm),
)
#set text(font: "Liberation Sans", size: 10pt, fill: rgb("#1F1F1F"))
#set par(justify: true, leading: 0.72em)
#set heading(numbering: none)

#let tone = rgb("#5A6B3A")
#let ink = rgb("#6A604E")
#let panel = rgb("#F5F0E6")
#let border = rgb("#CDBFA6")
#let warm = rgb("#EFE4D2")

#show heading.where(level: 1): it => block(below: 8pt)[
  text(size: 13pt, weight: "bold", fill: tone, it.body)
  v(3pt)
  line(length: 100%, stroke: (paint: border, thickness: 0.8pt))
]

#let stat(title, value) = block(
  inset: 10pt,
  fill: panel,
  stroke: (paint: border, thickness: 0.8pt),
  radius: 6pt,
)[
  #text(size: 8pt, fill: ink)[#title]
  #v(3pt)
  #text(size: 14pt, weight: "bold", fill: tone)[#value]
]

#let note_box(title, body) = block(
  inset: 10pt,
  fill: warm,
  stroke: (paint: border, thickness: 0.7pt),
  radius: 6pt,
)[
  #text(size: 8pt, tracking: 0.8pt, fill: ink)[#title]
  #v(4pt)
  #body
]

#align(center)[
  #text(size: 8pt, tracking: 1.8pt, fill: ink)[#doc_eyebrow]
  #v(4pt)
  #text(size: 22pt, weight: "bold")[#doc_title]
  #v(5pt)
  #text(size: 10pt, fill: ink)[#doc_subtitle]
]

#v(12pt)
"""
        serializer = GovTypstSerializer().dumps_all(
            {
                "doc_title": title,
                "doc_eyebrow": eyebrow,
                "doc_subtitle": subtitle,
                **bindings,
            }
        )
        return serializer + "\n" + theme.strip() + "\n\n" + body.strip() + "\n"

    @staticmethod
    def _fmt_date(value):
        if not value:
            return "-"
        value = fields.Date.to_date(value) if not isinstance(value, str) else fields.Date.to_date(value)
        return value.strftime("%d/%m/%Y")

    @staticmethod
    def _fmt_datetime(value):
        if not value:
            return "-"
        value = fields.Datetime.to_datetime(value) if not isinstance(value, str) else fields.Datetime.to_datetime(value)
        return value.strftime("%d/%m/%Y %H:%M")

    def _build_dossier_bindings(self):
        self.ensure_one()
        deadlines = self.prazo_ids.sorted(lambda item: (item.data_fim_real or item.data_fim_legal or fields.Date.today(), item.id))
        events = self.evento_ids.sorted(lambda item: (item.data_evento or fields.Datetime.now(), item.id), reverse=True)
        documents = self.documento_ids.sorted(lambda item: (item.create_date or fields.Datetime.now(), item.id), reverse=True)
        findings = self.apontamento_ids.sorted(lambda item: item.id, reverse=True)
        determinations = self.decisao_id.determination_ids.sorted(lambda item: (item.prazo_cumprimento or fields.Date.today(), item.id))
        return {
            "ciclo": {
                "nome": self.name,
                "company": self.company_id.display_name,
                "orgao": self.orgao_id.display_name,
                "tipo_prestacao": self._selection_label("tipo_prestacao", self.tipo_prestacao),
                "modo_dados": self._selection_label("modo_dados", self.modo_dados),
                "state": self._selection_label("state", self.state),
                "situacao_executiva": self._selection_label("situacao_executiva", self.situacao_executiva),
                "data_abertura": self._fmt_date(self.data_abertura),
                "data_remessa": self._fmt_date(self.data_remessa),
                "numero_protocolo": self.numero_protocolo or "-",
                "exercicio": self.exercicio_id.name or str(self._get_exercicio_label() or "-"),
            },
            "indicadores": {
                "proximo_vencimento": self._fmt_date(self.proximo_vencimento),
                "checklist_progresso": f"{self.checklist_progresso:.2f}%",
                "prazos_vencidos": self.prazo_vencido_count,
                "docs_pendentes": self.documento_pendente_count,
                "apontamentos_abertos": self.apontamento_aberto_count,
                "determinacoes_pendentes": self.determinacao_pendente_count,
                "cobertura_espelho": f"{self.cobertura_espelho_pct:.2f}%",
            },
            "responsaveis": [user.display_name for user in self.responsavel_ids],
            "prazos": [
                {
                    "descricao": item.descricao,
                    "tipo": self.env["gov.auditoria.prazo"]._fields["tipo"].selection and dict(self.env["gov.auditoria.prazo"]._fields["tipo"].selection).get(item.tipo, item.tipo),
                    "data_limite": self._fmt_date(item.data_fim_real or item.data_fim_legal),
                    "state": dict(self.env["gov.auditoria.prazo"]._fields["state"].selection).get(item.state, item.state),
                    "dias_restantes": item.dias_restantes,
                }
                for item in deadlines[:8]
            ],
            "eventos": [
                {
                    "tipo": dict(self.env["gov.auditoria.evento"]._fields["tipo"].selection).get(item.tipo, item.tipo),
                    "quando": self._fmt_datetime(item.data_evento),
                    "descricao": item.descricao or "-",
                }
                for item in events[:8]
            ],
            "documentos": [
                {
                    "nome": item.nome,
                    "tipo": dict(self.env["gov.auditoria.documento"]._fields["tipo"].selection).get(item.tipo, item.tipo),
                    "state": dict(self.env["gov.auditoria.documento"]._fields["state"].selection).get(item.state, item.state),
                    "protocolo": item.protocolo_externo or "-",
                }
                for item in documents[:10]
            ],
            "apontamentos": [
                {
                    "codigo": item.codigo or f"AP-{item.id}",
                    "tipo": dict(self.env["gov.auditoria.apontamento"]._fields["tipo"].selection).get(item.tipo, item.tipo),
                    "state": dict(self.env["gov.auditoria.apontamento"]._fields["state"].selection).get(item.state, item.state),
                    "descricao": item.descricao,
                }
                for item in findings[:8]
            ],
            "decisao": {
                "tipo": dict(self.env["gov.auditoria.decisao"]._fields["tipo"].selection).get(self.decisao_id.tipo, self.decisao_id.tipo) if self.decisao_id else "-",
                "numero": self.decisao_id.numero_acordao or "-" if self.decisao_id else "-",
                "data_acordao": self._fmt_date(self.decisao_id.data_acordao) if self.decisao_id else "-",
                "ementa": self.decisao_id.ementa or "-" if self.decisao_id else "-",
            },
            "determinacoes": [
                {
                    "descricao": item.descricao,
                    "prazo": self._fmt_date(item.prazo_cumprimento),
                    "state": dict(self.env["gov.auditoria.determinacao"]._fields["state"].selection).get(item.state, item.state),
                }
                for item in determinations[:8]
            ],
        }

    def _build_diligencia_bindings(self, event, deadline):
        self.ensure_one()
        return {
            "ciclo": {
                "nome": self.name,
                "company": self.company_id.display_name,
                "orgao": self.orgao_id.display_name,
                "sigla_orgao": self.orgao_id.sigla or "-",
                "portal": self.orgao_id.portal_url or "-",
                "instrucao": self.orgao_id.instrucao_normativa or "-",
                "protocolo": self.numero_protocolo or "-",
            },
            "evento": {
                "data_evento": self._fmt_datetime(event.data_evento),
                "descricao": event.descricao or "-",
                "responsavel": event.responsavel_id.display_name or "-",
            },
            "prazo": {
                "data_limite": self._fmt_date(deadline.data_fim_real or deadline.data_fim_legal) if deadline else "-",
                "dias": deadline.dias if deadline else 0,
            },
        }

    def _build_dossier_typst_source(self):
        self.ensure_one()
        data = self._build_dossier_bindings()
        body = r"""
#grid(columns: (1fr, 1fr, 1fr, 1fr), gutter: 10pt,
  [#stat("Situacao", ciclo.situacao_executiva)],
  [#stat("Estado", ciclo.state)],
  [#stat("Prox. vencimento", indicadores.proximo_vencimento)],
  [#stat("Checklist", indicadores.checklist_progresso)],
)

= Sumario
#outline(indent: 1.2em)

= Resumo do ciclo
- UG: #ciclo.company
- Orgao de controle: #ciclo.orgao
- Exercicio: #ciclo.exercicio
- Tipo de prestacao: #ciclo.tipo_prestacao
- Modo de dados: #ciclo.modo_dados
- Numero de protocolo: #ciclo.numero_protocolo
- Data de abertura: #ciclo.data_abertura
- Data de remessa: #ciclo.data_remessa

= Indicadores executivos
- Prazos vencidos: #indicadores.prazos_vencidos
- Documentos pendentes: #indicadores.docs_pendentes
- Apontamentos abertos: #indicadores.apontamentos_abertos
- Determinacoes pendentes: #indicadores.determinacoes_pendentes
- Cobertura de espelho: #indicadores.cobertura_espelho

= Responsaveis
#if len(responsaveis) == 0 [
  #text(fill: ink)[Nenhum responsavel vinculado.]
] else [
  #for item in responsaveis [
    - #item
  ]
]

= Prazos relevantes
#if len(prazos) == 0 [
  #text(fill: ink)[Nenhum prazo relevante no momento.]
] else [
  #for item in prazos [
    #note_box([#item.descricao], [
      #text(size: 9pt, fill: ink)[Tipo: #item.tipo | Limite: #item.data_limite | Estado: #item.state | Dias restantes: #item.dias_restantes]
    ])
    #v(5pt)
  ]
]

= Documentos do dossie
#if len(documentos) == 0 [
  #text(fill: ink)[Nenhum documento registrado.]
] else [
  #for item in documentos [
    - #item.nome (#item.tipo) | Estado: #item.state | Protocolo: #item.protocolo
  ]
]

= Eventos recentes
#if len(eventos) == 0 [
  #text(fill: ink)[Nenhum evento recente.]
] else [
  #for item in eventos [
    - #item.quando | #item.tipo
    #linebreak()
    #text(size: 9pt, fill: ink)[#item.descricao]
  ]
]

= Apontamentos
#if len(apontamentos) == 0 [
  #text(fill: ink)[Nenhum apontamento ativo.]
] else [
  #for item in apontamentos [
    #note_box([#item.codigo | #item.tipo | #item.state], [#item.descricao])
    #v(5pt)
  ]
]

= Decisao e cumprimento
- Tipo de decisao: #decisao.tipo
- Numero do acordao: #decisao.numero
- Data do acordao: #decisao.data_acordao
- Ementa: #decisao.ementa

#if len(determinacoes) == 0 [
  #text(fill: ink)[Sem determinacoes pendentes registradas.]
] else [
  #for item in determinacoes [
    - #item.descricao | Prazo: #item.prazo | Estado: #item.state
  ]
]
"""
        return self._render_typst_document(
            data,
            body,
            title=self.name,
            eyebrow="DOSSIE CONSOLIDADO DE AUDITORIA",
            subtitle="Espelho executivo, documental e decisorio do ciclo",
        )

    def _build_diligencia_typst_source(self, event, deadline):
        self.ensure_one()
        bindings = self._build_diligencia_bindings(event, deadline)
        body = r"""
#grid(columns: (1fr, 1fr, 1fr), gutter: 10pt,
  [#stat("Orgao", ciclo.sigla_orgao)],
  [#stat("Prazo final", prazo.data_limite)],
  [#stat("Protocolo base", ciclo.protocolo)],
)

= Notificacao
#note_box([Comunicacao oficial], [
  Foi emitida diligencia no ambito do ciclo #ciclo.nome, vinculada a #ciclo.orgao.
])

= Dados da diligencia
- UG: #ciclo.company
- Evento registrado em: #evento.data_evento
- Responsavel pelo registro: #evento.responsavel
- Prazo para resposta: #prazo.data_limite
- Dias previstos: #prazo.dias

= Texto da diligencia
#note_box([Descricao], [#evento.descricao])

= Referencias institucionais
- Portal do orgao: #ciclo.portal
- Instrucao normativa: #ciclo.instrucao

= Encaminhamento
Solicita-se protocolo da resposta, juntada documental e retorno no prazo consignado.
"""
        return self._render_typst_document(
            bindings,
            body,
            title="Notificacao de Diligencia",
            eyebrow="COMUNICACAO INSTITUCIONAL",
            subtitle="Peca pronta para remessa externa e protocolo do ciclo",
        )

    def _create_generated_document_from_typst(
        self,
        *,
        nome,
        tipo,
        typst_source,
        resumo,
        source_name,
        pdf_name,
        anexo_numero=False,
        event=False,
    ):
        self.ensure_one()
        pdf_bytes = GovTypstService.compile(typst_source, timeout=120)
        source_attachment = self.env["ir.attachment"].create(
            {
                "name": source_name,
                "datas": base64.b64encode(typst_source.encode("utf-8")).decode("ascii"),
                "mimetype": "text/plain",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        pdf_attachment = self.env["ir.attachment"].create(
            {
                "name": pdf_name,
                "datas": base64.b64encode(pdf_bytes).decode("ascii"),
                "mimetype": "application/pdf",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        existing = self.documento_ids.filtered(
            lambda doc: doc.tipo == tipo and doc.nome == nome and doc.state != "substituido"
        )[:1]
        version = (existing.versao + 1) if existing else 1
        if existing:
            existing.write({"state": "substituido"})
        values = {
            "ciclo_id": self.id,
            "event_id": event.id if event else False,
            "nome": nome,
            "tipo": tipo,
            "anexo_4320_numero": anexo_numero or False,
            "origem": "gerado_odoo",
            "attachment_id": pdf_attachment.id,
            "source_attachment_id": source_attachment.id,
            "hash_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
            "versao": version,
            "versao_anterior_id": existing.id if existing else False,
            "state": "finalizado",
            "resumo": resumo,
        }
        return self.env["gov.auditoria.documento"].create(values)

    def _generate_dossier_document(self):
        self.ensure_one()
        typst_source = self._build_dossier_typst_source()
        document = self._create_generated_document_from_typst(
            nome=f"Dossie Consolidado - {self.name}",
            tipo="relatorio",
            typst_source=typst_source,
            resumo="Dossie consolidado do ciclo gerado em Typst.",
            source_name=f"dossie_auditoria_{self.company_id.id}_{self._get_exercicio_label() or 'sem_exercicio'}.typ",
            pdf_name=f"dossie_auditoria_{self.company_id.id}_{self._get_exercicio_label() or 'sem_exercicio'}.pdf",
        )
        self.message_post(
            body=(
                "Dossie consolidado gerado em Typst. "
                f"SHA-256: <code>{(document.hash_sha256 or '')[:16]}...</code>"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def _generate_diligencia_document(self):
        self.ensure_one()
        event = self.evento_ids.filtered(lambda item: item.tipo == "diligencia_emitida")[:1]
        if not event:
            raise UserError("Nao existe diligencia registrada para gerar a notificacao.")
        deadline = self.prazo_ids.filtered(
            lambda item: item.evento_id == event and item.descricao == "Prazo de resposta a diligencia"
        )[:1]
        typst_source = self._build_diligencia_typst_source(event, deadline)
        document = self._create_generated_document_from_typst(
            nome=f"Notificacao de Diligencia - {self.name}",
            tipo="notificacao",
            typst_source=typst_source,
            resumo="Notificacao de diligencia gerada em Typst para remessa externa.",
            source_name=f"diligencia_{self.id}_{event.id}.typ",
            pdf_name=f"diligencia_{self.id}_{event.id}.pdf",
            event=event,
        )
        event.documento_ids = [(4, document.id)]
        self.message_post(
            body="Notificacao de diligencia gerada em Typst para protocolo externo.",
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return document

    def action_generate_mvp_annexes(self):
        for rec in self:
            if not rec.reporting_ready:
                raise UserError("O ciclo nao atende os pre-requisitos para gerar os anexos MVP.")
            annexes = [
                ("12", "Balanco Orcamentario"),
                ("13", "Balanco Financeiro"),
                ("14", "Balanco Patrimonial"),
                ("15", "Demonstracao das Variacoes Patrimoniais"),
            ]
            for number, title in annexes:
                rec._generate_annex_document(number, title)
        return True

    def _generate_annex_document(self, anexo_numero, title):
        self.ensure_one()
        body = self._build_annex_html(anexo_numero, title)
        filename = f"anexo_{anexo_numero}_{self.company_id.id}_{self._get_exercicio_label()}.html"
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "datas": base64.b64encode(body.encode("utf-8")).decode("ascii"),
                "mimetype": "text/html",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        existing = self.documento_ids.filtered(
            lambda doc: doc.tipo == "anexo_4320" and doc.anexo_4320_numero == anexo_numero and doc.state != "substituido"
        )[:1]
        version = (existing.versao + 1) if existing else 1
        if existing:
            existing.write({"state": "substituido"})
        sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.env["gov.auditoria.documento"].create(
            {
                "ciclo_id": self.id,
                "nome": title,
                "tipo": "anexo_4320",
                "anexo_4320_numero": anexo_numero,
                "origem": "gerado_odoo",
                "attachment_id": attachment.id,
                "hash_sha256": sha256,
                "versao": version,
                "versao_anterior_id": existing.id if existing else False,
                "state": "finalizado",
            }
        )

    def _build_annex_html(self, anexo_numero, title):
        self.ensure_one()
        exercicio = self._get_exercicio_label() or "-"
        return (
            "<html><body>"
            f"<h1>{title} - Anexo {anexo_numero}</h1>"
            f"<p><strong>UG:</strong> {self.company_id.display_name}</p>"
            f"<p><strong>Exercicio:</strong> {exercicio}</p>"
            f"<p><strong>Modo:</strong> {self.modo_dados}</p>"
            f"<p><strong>Empenhos:</strong> {self.native_empenho_count}</p>"
            f"<p><strong>Liquidacoes:</strong> {self.native_liquidacao_count}</p>"
            f"<p><strong>Pagamentos:</strong> {self.native_pagamento_count}</p>"
            f"<p><strong>Cobertura Espelho:</strong> {self.cobertura_espelho_pct:.2f}%</p>"
            "</body></html>"
        )
