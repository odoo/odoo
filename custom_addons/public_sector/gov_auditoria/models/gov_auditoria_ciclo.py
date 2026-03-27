import base64
import hashlib
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


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
    ultimo_evento_em = fields.Datetime(compute="_compute_event_metrics", store=False)
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

    @api.depends("evento_ids.data_evento")
    def _compute_event_metrics(self):
        for rec in self:
            rec.ultimo_evento_em = max(rec.evento_ids.mapped("data_evento"), default=False)

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

    def write(self, vals):
        if not self.env.user.has_group("gov_auditoria.group_auditoria_admin"):
            locked_cycles = self.filtered(lambda rec: rec.state in ("encerrado", "arquivado"))
            if locked_cycles:
                raise UserError("Ciclos encerrados ou arquivados sao somente leitura para este perfil.")
        return super().write(vals)

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
