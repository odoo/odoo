from odoo import api, fields, models
from odoo.exceptions import UserError


class GovEmpenhoWizard(models.TransientModel):
    _name = "gov.empenho.wizard"
    _description = "Wizard de Emissão de NE a partir do Processo"

    processo_id = fields.Many2one(
        "gov.processo",
        required=True,
        readonly=True,
    )

    dotacao_id = fields.Many2one(
        "gov.processo.dotacao",
        string="Dotação do Processo",
        domain="[('processo_id', '=', processo_id), ('reservado', '=', False)]",
        help=(
            "Selecione a indicação orçamentária do processo. "
            "Apenas dotações não reservadas."
        ),
    )

    programa = fields.Char(string="Programa")
    acao = fields.Char(string="Ação")
    natureza_despesa = fields.Char(string="Natureza da Despesa")
    fonte_recurso = fields.Char(string="Fonte de Recurso")
    exercicio = fields.Integer(
        string="Exercício",
        default=lambda self: fields.Date.today().year,
    )

    credor_id = fields.Many2one(
        "res.partner",
        string="Credor (Fornecedor)",
        required=True,
        domain="[('is_company', '=', True)]",
    )

    tipo_empenho = fields.Selection(
        [
            ("ordinario", "Ordinário"),
            ("estimativo", "Estimativo"),
            ("global", "Global"),
        ],
        default="ordinario",
        required=True,
    )

    valor_empenho = fields.Monetary(
        string="Valor do Empenho",
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    objeto = fields.Text(
        string="Objeto do Empenho",
        required=True,
    )

    data_empenho = fields.Date(default=fields.Date.today)
    data_vencimento = fields.Date(string="Vencimento")

    retroativo = fields.Boolean(default=False)
    urgencia = fields.Boolean(default=False)

    alerta_sem_dotacao = fields.Boolean(
        compute="_compute_alertas",
        store=False,
    )
    alerta_valor_excede = fields.Boolean(
        compute="_compute_alertas",
        store=False,
    )
    valor_dotacao_disponivel = fields.Monetary(
        string="Valor disponível na dotação",
        currency_field="currency_id",
        compute="_compute_alertas",
        store=False,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        processo_id = vals.get("processo_id") or self.env.context.get("default_processo_id")
        if not processo_id:
            return vals

        processo = self.env["gov.processo"].browse(processo_id)
        if not processo.exists():
            return vals

        vals.setdefault("retroativo", processo.retroativo)
        vals.setdefault("urgencia", processo.urgencia)
        vals.setdefault("objeto", processo.subject or "")
        vals.setdefault("exercicio", fields.Date.today().year)

        dotacao = processo.dotacao_ids.filtered(lambda d: not d.reservado)[:1]
        if dotacao:
            vals.setdefault("dotacao_id", dotacao.id)
            vals.setdefault("programa", dotacao.programa or "")
            vals.setdefault("acao", dotacao.acao or "")
            vals.setdefault("natureza_despesa", dotacao.natureza_despesa or "")
            vals.setdefault("fonte_recurso", dotacao.fonte_recurso or "")
            vals.setdefault("exercicio", dotacao.exercicio or vals.get("exercicio"))
            vals.setdefault("valor_empenho", dotacao.valor_estimado or 0.0)

        return vals

    @api.depends("dotacao_id", "valor_empenho", "processo_id")
    def _compute_alertas(self):
        for rec in self:
            if not rec.dotacao_id:
                rec.alerta_sem_dotacao = True
                rec.alerta_valor_excede = False
                rec.valor_dotacao_disponivel = 0.0
                continue

            rec.alerta_sem_dotacao = False
            disponivel = rec.dotacao_id.valor_estimado or 0.0
            rec.valor_dotacao_disponivel = disponivel
            rec.alerta_valor_excede = bool(rec.valor_empenho and rec.valor_empenho > disponivel)

    @api.onchange("dotacao_id")
    def _onchange_dotacao(self):
        if self.dotacao_id:
            self.programa = self.dotacao_id.programa
            self.acao = self.dotacao_id.acao
            self.natureza_despesa = self.dotacao_id.natureza_despesa
            self.fonte_recurso = self.dotacao_id.fonte_recurso
            self.exercicio = self.dotacao_id.exercicio
            if not self.valor_empenho:
                self.valor_empenho = self.dotacao_id.valor_estimado

    @api.onchange("processo_id")
    def _onchange_processo(self):
        if self.processo_id:
            processo = self.processo_id
            self.retroativo = processo.retroativo
            self.urgencia = processo.urgencia
            if not self.objeto and processo.subject:
                self.objeto = processo.subject

    def action_emitir_ne(self):
        self.ensure_one()

        if not self.credor_id:
            raise UserError("Informe o credor do empenho.")
        if (self.valor_empenho or 0.0) <= 0:
            raise UserError("Valor do empenho deve ser maior que zero.")

        ne = self.env["gov.empenho"].create(
            {
                "ug_id": self.processo_id.ug_id.id,
                "exercicio": self.exercicio,
                "credor_id": self.credor_id.id,
                "tipo_empenho": self.tipo_empenho,
                "valor_empenho": self.valor_empenho,
                "data_empenho": self.data_empenho,
                "data_vencimento": self.data_vencimento or False,
                "objeto": self.objeto,
                "programa": self.programa or "",
                "acao": self.acao or "",
                "natureza_despesa": self.natureza_despesa or "",
                "fonte_recurso": self.fonte_recurso or "",
                "dotacao_id": self.dotacao_id.id if self.dotacao_id else False,
                "processo_id_ref": self.processo_id.id,
                "retroativo": self.retroativo,
                "urgencia": self.urgencia,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": f"NE - {ne.name}",
            "res_model": "gov.empenho",
            "res_id": ne.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_criar_rascunho(self):
        self.ensure_one()
        if not self.credor_id:
            raise UserError("Informe o credor do empenho.")
        if (self.valor_empenho or 0.0) <= 0:
            raise UserError("Valor do empenho deve ser maior que zero.")

        ne = self.env["gov.empenho"].create(
            {
                "ug_id": self.processo_id.ug_id.id,
                "exercicio": self.exercicio,
                "credor_id": self.credor_id.id,
                "tipo_empenho": self.tipo_empenho,
                "valor_empenho": self.valor_empenho,
                "data_empenho": self.data_empenho,
                "data_vencimento": self.data_vencimento or False,
                "objeto": self.objeto,
                "programa": self.programa or "",
                "acao": self.acao or "",
                "natureza_despesa": self.natureza_despesa or "",
                "fonte_recurso": self.fonte_recurso or "",
                "dotacao_id": self.dotacao_id.id if self.dotacao_id else False,
                "processo_id_ref": self.processo_id.id,
                "retroativo": self.retroativo,
                "urgencia": self.urgencia,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": f"NE - {ne.name}",
            "res_model": "gov.empenho",
            "res_id": ne.id,
            "view_mode": "form",
            "target": "current",
        }
