from datetime import timedelta

from odoo import api, fields, models


class GovAuditoriaDecisao(models.Model):
    _name = "gov.auditoria.decisao"
    _description = "Final Decision"
    _order = "data_acordao desc, id desc"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="ciclo_id.currency_id", store=True, readonly=True)
    tipo = fields.Selection(
        [
            ("regular", "Regular"),
            ("regular_com_ressalvas", "Regular com Ressalvas"),
            ("irregular", "Irregular"),
            ("em_recurso", "Em Recurso"),
        ],
        required=True,
        default="regular",
    )
    numero_acordao = fields.Char()
    data_acordao = fields.Date(required=True, default=fields.Date.today)
    data_publicacao = fields.Date()
    ementa = fields.Text()
    valor_condenacao = fields.Monetary(currency_field="currency_id")
    apontamento_ids = fields.Many2many("gov.auditoria.apontamento", string="Apontamentos")
    prazo_recurso_dias = fields.Integer(default=0)
    data_limite_recurso = fields.Date(compute="_compute_data_limite_recurso", store=True)
    data_transito = fields.Date()
    attachment_ids = fields.Many2many("ir.attachment", string="Anexos")
    determination_ids = fields.One2many("gov.auditoria.determinacao", "decisao_id", string="Determinacoes")
    state = fields.Selection(
        [
            ("minuta", "Minuta"),
            ("publicado", "Publicado"),
            ("transitado", "Transitado"),
        ],
        default="publicado",
        required=True,
    )

    @api.depends("data_acordao", "prazo_recurso_dias")
    def _compute_data_limite_recurso(self):
        for rec in self:
            if rec.data_acordao and rec.prazo_recurso_dias:
                rec.data_limite_recurso = rec.data_acordao + timedelta(days=rec.prazo_recurso_dias)
            else:
                rec.data_limite_recurso = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.ciclo_id.write({"decisao_id": rec.id})
        return records

    def action_mark_transitado(self):
        for rec in self:
            rec.write(
                {
                    "state": "transitado",
                    "data_transito": rec.data_transito or fields.Date.today(),
                }
            )
            rec.ciclo_id.action_to_acordao()

    def action_generate_acordao_typst(self):
        for rec in self:
            rec._generate_acordao_document()
        return True

    def _build_acordao_typst_source(self):
        self.ensure_one()
        bindings = {
            "decisao": {
                "tipo": dict(self._fields["tipo"].selection).get(self.tipo, self.tipo),
                "numero": self.numero_acordao or "-",
                "data_acordao": self.ciclo_id._fmt_date(self.data_acordao),
                "data_publicacao": self.ciclo_id._fmt_date(self.data_publicacao),
                "data_limite_recurso": self.ciclo_id._fmt_date(self.data_limite_recurso),
                "ementa": self.ementa or "-",
                "valor_condenacao": f"{self.valor_condenacao:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if self.valor_condenacao
                else "0,00",
            },
            "ciclo": {
                "nome": self.ciclo_id.name,
                "company": self.ciclo_id.company_id.display_name,
                "orgao": self.ciclo_id.orgao_id.display_name,
            },
            "determinacoes": [
                {
                    "descricao": item.descricao,
                    "prazo": self.ciclo_id._fmt_date(item.prazo_cumprimento),
                    "state": dict(self.env["gov.auditoria.determinacao"]._fields["state"].selection).get(item.state, item.state),
                }
                for item in self.determination_ids
            ],
        }
        body = r"""
#grid(columns: (1fr, 1fr, 1fr), gutter: 10pt,
  [#stat("Acordao", decisao.numero)],
  [#stat("Tipo", decisao.tipo)],
  [#stat("Limite recurso", decisao.data_limite_recurso)],
)

= Contexto institucional
- Ciclo: #ciclo.nome
- UG: #ciclo.company
- Orgao julgador: #ciclo.orgao
- Data do acordao: #decisao.data_acordao
- Data da publicacao: #decisao.data_publicacao

= Ementa
#note_box([Ementa], [#decisao.ementa])

= Condenacao e recurso
- Valor de condenacao: #decisao.valor_condenacao
- Prazo limite recursal: #decisao.data_limite_recurso

= Determinacoes
#if len(determinacoes) == 0 [
  #text(fill: ink)[Nao ha determinacoes registradas para esta decisao.]
] else [
  #for item in determinacoes [
    - #item.descricao | Prazo: #item.prazo | Estado: #item.state
  ]
]
"""
        return self.ciclo_id._render_typst_document(
            bindings,
            body,
            title=f"Acordao {self.numero_acordao or '-'}",
            eyebrow="ESPELHO DECISORIO",
            subtitle="Documento institucional da decisao registrada no ciclo",
        )

    def _generate_acordao_document(self):
        self.ensure_one()
        typst_source = self._build_acordao_typst_source()
        document = self.ciclo_id._create_generated_document_from_typst(
            nome=f"Acordao Typst - {self.numero_acordao or self.ciclo_id.name}",
            tipo="acordao",
            typst_source=typst_source,
            resumo="Espelho decisorio gerado em Typst para o acordao do ciclo.",
            source_name=f"acordao_{self.ciclo_id.id}_{self.id}.typ",
            pdf_name=f"acordao_{self.ciclo_id.id}_{self.id}.pdf",
        )
        self.attachment_ids = [(4, document.attachment_id.id), (4, document.source_attachment_id.id)]
        return document


class GovAuditoriaDeterminacao(models.Model):
    _name = "gov.auditoria.determinacao"
    _description = "Decision Determination"
    _order = "prazo_cumprimento, id"

    decisao_id = fields.Many2one("gov.auditoria.decisao", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="decisao_id.company_id", store=True, readonly=True)
    descricao = fields.Text(required=True)
    prazo_cumprimento = fields.Date()
    prazo_id = fields.Many2one("gov.auditoria.prazo", ondelete="set null")
    responsavel_id = fields.Many2one("res.partner")
    evidencia_ids = fields.Many2many("ir.attachment", string="Evidencias")
    data_cumprimento = fields.Date()
    state = fields.Selection(
        [
            ("pendente", "Pendente"),
            ("cumprido", "Cumprido"),
            ("parcial", "Parcial"),
            ("descumprido", "Descumprido"),
        ],
        default="pendente",
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_deadline_records()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._sync_deadline_records()
        return result

    def _sync_deadline_records(self):
        Prazo = self.env["gov.auditoria.prazo"]
        cycles = self.env["gov.auditoria.ciclo"]
        for rec in self:
            ciclo = rec.decisao_id.ciclo_id
            if not ciclo:
                continue
            cycles |= ciclo
            if rec.prazo_cumprimento:
                prazo_vals = {
                    "ciclo_id": ciclo.id,
                    "tipo": "interno",
                    "descricao": f"Cumprimento de determinacao: {rec.descricao[:80]}",
                    "data_inicio": rec.decisao_id.data_acordao or fields.Date.today(),
                    "data_fim_legal": rec.prazo_cumprimento,
                }
                if rec.prazo_id:
                    rec.prazo_id.write(prazo_vals)
                else:
                    rec.prazo_id = Prazo.create(prazo_vals).id
            elif rec.prazo_id:
                rec.prazo_id.unlink()
                rec.prazo_id = False

            if rec.prazo_id and rec.state == "cumprido":
                rec.prazo_id.write({"state": "cumprido"})
        cycles._sync_operational_activities()

    def action_mark_cumprido(self):
        for rec in self:
            rec.write(
                {
                    "state": "cumprido",
                    "data_cumprimento": rec.data_cumprimento or fields.Date.today(),
                }
            )
            self.env["gov.auditoria.evento"].create(
                {
                    "ciclo_id": rec.decisao_id.ciclo_id.id,
                    "tipo": "determinacao_cumprida",
                    "data_evento": fields.Datetime.now(),
                    "descricao": rec.descricao,
                    "responsavel_id": self.env.user.id,
                    "origem": "manual",
                    "state": "concluido",
                }
            )
        self.mapped("decisao_id.ciclo_id")._sync_operational_activities()
        return True
