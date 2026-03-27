from odoo import api, fields, models


class GovAuditoriaApontamento(models.Model):
    _name = "gov.auditoria.apontamento"
    _description = "Audit Finding"
    _order = "id desc"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="ciclo_id.currency_id", store=True, readonly=True)
    codigo = fields.Char()
    descricao = fields.Text(required=True)
    tipo = fields.Selection(
        [
            ("irregularidade", "Irregularidade"),
            ("ressalva", "Ressalva"),
            ("recomendacao", "Recomendacao"),
            ("determinacao", "Determinacao"),
            ("multa", "Multa"),
        ],
        required=True,
        default="irregularidade",
    )
    valor_multa = fields.Monetary(currency_field="currency_id")
    responsavel_ids = fields.Many2many("res.partner", string="Responsaveis")
    prazo_defesa_id = fields.Many2one("gov.auditoria.prazo", ondelete="set null")
    resposta = fields.Text()
    data_resposta = fields.Date()
    documento_resposta_ids = fields.Many2many(
        "gov.auditoria.documento",
        "gov_auditoria_apontamento_documento_rel",
        "apontamento_id",
        "documento_id",
        string="Docs de Resposta",
    )
    state = fields.Selection(
        [
            ("aberto", "Aberto"),
            ("respondido", "Respondido"),
            ("acatado", "Acatado"),
            ("rejeitado", "Rejeitado"),
        ],
        default="aberto",
        required=True,
    )
    decisao_id = fields.Many2one("gov.auditoria.decisao", ondelete="set null")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("ciclo_id")._sync_operational_activities()
        return records

    def write(self, vals):
        result = super().write(vals)
        self.mapped("ciclo_id")._sync_operational_activities()
        return result

    def action_open_resposta_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Registrar Resposta",
            "res_model": "gov.auditoria.apontamento.resposta.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_ciclo_id": self.ciclo_id.id,
                "default_apontamento_id": self.id,
            },
        }

    def action_mark_acatado(self):
        for rec in self:
            rec.state = "acatado"
        return True

    def action_mark_rejeitado(self):
        for rec in self:
            rec.state = "rejeitado"
        return True

    def action_generate_resposta_typst(self):
        for rec in self:
            rec._generate_resposta_document()
        return True

    def _build_resposta_typst_source(self):
        self.ensure_one()
        responsaveis = ", ".join(self.responsavel_ids.mapped("display_name")) or "-"
        bindings = {
            "apontamento": {
                "codigo": self.codigo or f"AP-{self.id}",
                "tipo": dict(self._fields["tipo"].selection).get(self.tipo, self.tipo),
                "state": dict(self._fields["state"].selection).get(self.state, self.state),
                "responsaveis": responsaveis,
                "descricao": self.descricao or "-",
                "resposta": self.resposta or "-",
                "data_resposta": self.ciclo_id._fmt_date(self.data_resposta),
                "prazo_defesa": self.ciclo_id._fmt_date(
                    self.prazo_defesa_id.data_fim_real or self.prazo_defesa_id.data_fim_legal
                )
                if self.prazo_defesa_id
                else "-",
            },
            "ciclo": {
                "nome": self.ciclo_id.name,
                "company": self.ciclo_id.company_id.display_name,
                "orgao": self.ciclo_id.orgao_id.display_name,
            },
        }
        body = r"""
#grid(columns: (1fr, 1fr, 1fr), gutter: 10pt,
  [#stat("Apontamento", apontamento.codigo)],
  [#stat("Tipo", apontamento.tipo)],
  [#stat("Prazo defesa", apontamento.prazo_defesa)],
)

= Contexto
- Ciclo: #ciclo.nome
- UG: #ciclo.company
- Orgao de controle: #ciclo.orgao
- Estado do apontamento: #apontamento.state
- Responsaveis: #apontamento.responsaveis

= Descricao do apontamento
#note_box([Registro], [#apontamento.descricao])

= Resposta formal
#note_box([Defesa], [#apontamento.resposta])

= Fechamento
- Data da resposta: #apontamento.data_resposta
"""
        return self.ciclo_id._render_typst_document(
            bindings,
            body,
            title=f"Resposta ao {self.codigo or f'AP-{self.id}'}",
            eyebrow="PECA DE DEFESA",
            subtitle="Manifestacao formal gerada a partir do apontamento do ciclo",
        )

    def _generate_resposta_document(self):
        self.ensure_one()
        if not self.resposta:
            return False
        typst_source = self._build_resposta_typst_source()
        document = self.ciclo_id._create_generated_document_from_typst(
            nome=f"Defesa Typst - {self.codigo or f'AP-{self.id}'}",
            tipo="defesa",
            typst_source=typst_source,
            resumo="Peca de defesa gerada em Typst a partir do apontamento.",
            source_name=f"defesa_{self.ciclo_id.id}_{self.id}.typ",
            pdf_name=f"defesa_{self.ciclo_id.id}_{self.id}.pdf",
        )
        self.documento_resposta_ids = [(4, document.id)]
        return document
