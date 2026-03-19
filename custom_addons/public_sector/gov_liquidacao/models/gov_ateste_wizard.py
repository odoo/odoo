import logging

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CHECKLIST_ITEMS = [
    {
        "key": "nf_valida",
        "label": "Nota Fiscal / Fatura valida e dentro do prazo",
        "critico": True,
        "norma": "Lei 14.133/2021, Art. 140",
    },
    {
        "key": "objeto_conforme",
        "label": "Objeto entregue conforme especificacao do contrato / TR",
        "critico": True,
        "norma": "Lei 14.133/2021, Art. 140, §1º",
    },
    {
        "key": "prazo_cumprido",
        "label": "Prazo de entrega cumprido ou justificativa registrada",
        "critico": True,
        "norma": "Lei 14.133/2021, Art. 140, §2º",
    },
    {
        "key": "quantidade_conferida",
        "label": "Quantidade / extensao conferida e compativel com NF",
        "critico": True,
        "norma": "MPDG - Manual de Gestao de Contratos",
    },
    {
        "key": "qualidade_aceita",
        "label": "Qualidade / acabamento aceito pelo fiscal do contrato",
        "critico": False,
        "norma": "Lei 14.133/2021, Art. 117",
    },
    {
        "key": "docs_aceite_anexados",
        "label": "Documentos de aceite / relatorio de recebimento anexados",
        "critico": False,
        "norma": "TCU - Acordao 1.214/2013",
    },
    {
        "key": "retencoes_corretas",
        "label": "Retencoes fiscais (IR, ISS, INSS) calculadas corretamente",
        "critico": False,
        "norma": "RFB - IN 1.234/2012",
    },
]


class GovAtesteWizard(models.TransientModel):
    _name = "gov.ateste.wizard"
    _description = "Wizard de Ateste de Recebimento - NL"

    liquidacao_id = fields.Many2one(
        "gov.liquidacao",
        string="Nota de Liquidacao",
        required=True,
        readonly=True,
    )
    nl_name = fields.Char(
        related="liquidacao_id.name",
        readonly=True,
    )
    nl_valor = fields.Monetary(
        related="liquidacao_id.valor_liquidado",
        currency_field="currency_id",
        readonly=True,
    )
    nl_credor = fields.Char(
        related="liquidacao_id.credor_id.name",
        readonly=True,
    )
    nl_empenho = fields.Char(
        related="liquidacao_id.empenho_name",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    atestante_id = fields.Many2one(
        "res.users",
        string="Atestante",
        required=True,
        default=lambda self: self.env.user,
    )
    observacao = fields.Text(
        string="Observacao do Ateste",
        help="Registre ressalvas ou observacoes relevantes.",
    )

    chk_nf_valida = fields.Boolean("NF/Fatura valida")
    chk_objeto_conforme = fields.Boolean("Objeto conforme")
    chk_prazo_cumprido = fields.Boolean("Prazo cumprido")
    chk_quantidade = fields.Boolean("Quantidade conferida")
    chk_qualidade = fields.Boolean("Qualidade aceita")
    chk_docs_anexados = fields.Boolean("Documentos anexados")
    chk_retencoes = fields.Boolean("Retencoes corretas")

    score_conformidade = fields.Integer(
        string="Score de Conformidade (%)",
        compute="_compute_score",
        store=False,
    )
    score_badge = fields.Char(
        string="Badge",
        compute="_compute_score",
        store=False,
    )
    itens_criticos_pendentes = fields.Char(
        string="Itens criticos pendentes",
        compute="_compute_score",
        store=False,
    )
    pode_atestar = fields.Boolean(
        compute="_compute_score",
        store=False,
    )

    resumo_checklist = fields.Text(
        compute="_compute_resumo_checklist",
        store=False,
    )

    @api.depends(
        "chk_nf_valida",
        "chk_objeto_conforme",
        "chk_prazo_cumprido",
        "chk_quantidade",
        "chk_qualidade",
        "chk_docs_anexados",
        "chk_retencoes",
    )
    def _compute_score(self):
        campo_map = {
            "nf_valida": "chk_nf_valida",
            "objeto_conforme": "chk_objeto_conforme",
            "prazo_cumprido": "chk_prazo_cumprido",
            "quantidade_conferida": "chk_quantidade",
            "qualidade_aceita": "chk_qualidade",
            "docs_aceite_anexados": "chk_docs_anexados",
            "retencoes_corretas": "chk_retencoes",
        }
        total = len(CHECKLIST_ITEMS)
        for rec in self:
            marcados = 0
            criticos_pendentes = []
            for item in CHECKLIST_ITEMS:
                campo = campo_map.get(item["key"], "")
                valor = getattr(rec, campo, False)
                if valor:
                    marcados += 1
                elif item["critico"]:
                    criticos_pendentes.append(item["label"])

            score = round(marcados / total * 100) if total else 0
            rec.score_conformidade = score
            rec.score_badge = (
                "APROVADO"
                if score >= 80 and not criticos_pendentes
                else "ATENCAO"
                if score >= 50
                else "INSUFICIENTE"
            )
            rec.itens_criticos_pendentes = (
                "\n".join(f"• {item}" for item in criticos_pendentes) if criticos_pendentes else ""
            )
            rec.pode_atestar = not bool(criticos_pendentes)

    @api.depends(
        "chk_nf_valida",
        "chk_objeto_conforme",
        "chk_prazo_cumprido",
        "chk_quantidade",
        "chk_qualidade",
        "chk_docs_anexados",
        "chk_retencoes",
    )
    def _compute_resumo_checklist(self):
        campo_map = {
            "nf_valida": "chk_nf_valida",
            "objeto_conforme": "chk_objeto_conforme",
            "prazo_cumprido": "chk_prazo_cumprido",
            "quantidade_conferida": "chk_quantidade",
            "qualidade_aceita": "chk_qualidade",
            "docs_aceite_anexados": "chk_docs_anexados",
            "retencoes_corretas": "chk_retencoes",
        }
        for rec in self:
            linhas = []
            for item in CHECKLIST_ITEMS:
                campo = campo_map.get(item["key"], "")
                valor = getattr(rec, campo, False)
                critico = " (CRÍTICO)" if item["critico"] else ""
                marca = "OK" if valor else "PENDENTE"
                linhas.append(f"[{marca}] {item['label']}{critico}\nNorma: {item['norma']}")
            rec.resumo_checklist = "\n\n".join(linhas)

    def action_atestar(self):
        self.ensure_one()
        if not self.pode_atestar:
            raise UserError(
                "Nao e possivel atestar: itens criticos do checklist AGU nao foram confirmados.\n\n"
                f"{self.itens_criticos_pendentes}"
            )

        nl = self.liquidacao_id
        nl.write(
            {
                "atestante_id": self.atestante_id.id,
                "observacao_ateste": self.observacao or "",
            }
        )
        nl.action_atestar()

        nl.message_post(
            body=Markup(
                f"<b>Checklist AGU - Ateste</b><br/>"
                f"Score: <b>{self.score_conformidade}%</b> {self.score_badge}<br/>"
                f"Atestante: {self.atestante_id.name}<br/>"
                + (f"<br/><b>Observacao:</b> {self.observacao}" if self.observacao else "")
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        self._criar_activity_liquidar()
        return {"type": "ir.actions.act_window_close"}

    def action_atestar_com_ressalva(self):
        self.ensure_one()
        if not self.observacao or not self.observacao.strip():
            raise UserError(
                "Para atestar com ressalva, registre a observacao explicando os itens nao verificados."
            )
        if self.itens_criticos_pendentes:
            raise UserError(
                "Ateste com ressalva nao e permitido quando ha itens CRITICOS pendentes.\n\n"
                f"{self.itens_criticos_pendentes}"
            )
        return self.action_atestar()

    def _criar_activity_liquidar(self):
        nl = self.liquidacao_id
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            _logger.warning("mail_activity_data_todo nao encontrado para agendar activity da NL %s", nl.id)
            return

        gestor = nl.atestante_id or self.env.user
        nl.activity_schedule(
            activity_type_id=activity_type.id,
            summary=f"Confirmar liquidacao {nl.name}",
            note=Markup(
                f"Liquidacao <b>{nl.name}</b> atestada por {self.atestante_id.name}.<br/>"
                f"Valor: R$ {nl.valor_liquidado:,.2f}<br/>"
                f"Acao: clique em <b>Confirmar Liquidacao</b> para prosseguir."
            ),
            user_id=gestor.id,
        )
