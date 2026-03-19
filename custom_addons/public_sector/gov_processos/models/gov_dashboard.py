import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError


_logger = logging.getLogger(__name__)


class GovDashboard(models.AbstractModel):
    _name = "gov.dashboard"
    _description = "Painel Executivo AGI Gov"

    ug_id = fields.Many2one("res.company", string="UG", readonly=True)

    total_processos = fields.Integer(readonly=True)
    em_demanda = fields.Integer(string="Demanda", readonly=True)
    em_instrucao = fields.Integer(string="Instrução", readonly=True)
    em_planejamento = fields.Integer(string="Planejamento", readonly=True)
    em_licitacao = fields.Integer(string="Licitação", readonly=True)
    em_contratacao = fields.Integer(string="Contratação", readonly=True)
    em_execucao = fields.Integer(string="Execução", readonly=True)
    encerrados_mes = fields.Integer(string="Enc./Mês", readonly=True)

    prazos_vencidos = fields.Integer(string="Prazos Vencidos", readonly=True)
    prazos_proximos = fields.Integer(string="Vencendo em 7d", readonly=True)
    processos_inertes = fields.Integer(string="Parados >21d", readonly=True)
    urgentes_ativos = fields.Integer(string="Urgentes Ativos", readonly=True)
    retroativos_ativos = fields.Integer(string="Retroativos", readonly=True)

    valor_total_estimado = fields.Monetary(
        string="Valor Total (Estimado)",
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one("res.currency", readonly=True)

    docs_em_revisao = fields.Integer(string="Docs em Revisão", readonly=True)
    docs_ia_pendentes = fields.Integer(string="Docs IA p/ Revisão", readonly=True)

    @api.model
    def get_dashboard_data(self, ug_id=None):
        """
        Retorna KPIs executivos do AGI Gov por UG.
        Se ug_id for None, consolida todas as UGs visíveis do usuário.
        """
        try:
            hoje = fields.Date.today()
            alerta_ate = hoje + relativedelta(days=7)
            limite_inercia = fields.Datetime.now() - relativedelta(days=21)
            inicio_mes = hoje.replace(day=1)

            Processo = self.env["gov.processo"]
            Tramite = self.env["gov.processo.tramite"]
            Doc = self.env["gov.processo.doc"]
            Empenho = self.env.get("gov.empenho")
            Liquidacao = self.env.get("gov.liquidacao")

            domain_base = [("ug_id", "=", ug_id)] if ug_id else []

            def count(domain):
                return Processo.search_count(domain_base + domain)

            estados_ativos = [
                "instrucao",
                "planejamento",
                "licitacao",
                "contratacao",
                "execucao",
            ]

            kpis = {
                "total_processos": count([]),
                "total_ativos": count([("state", "in", estados_ativos + ["demanda"])]),
                "em_demanda": count([("state", "=", "demanda")]),
                "em_instrucao": count([("state", "=", "instrucao")]),
                "em_planejamento": count([("state", "=", "planejamento")]),
                "em_licitacao": count([("state", "=", "licitacao")]),
                "em_contratacao": count([("state", "=", "contratacao")]),
                "em_execucao": count([("state", "=", "execucao")]),
                "encerrados_mes": count(
                    [
                        ("state", "=", "encerrado"),
                        ("write_date", ">=", str(inicio_mes)),
                    ]
                ),
                # Compatibilidade com widgets executivos consolidados.
                "processos_criticos": 0,
                "total_empenhos": 0.0,
                "total_liquidado": 0.0,
            }

            alertas = {
                "prazos_vencidos": count(
                    [
                        ("prazo_resposta", "<", hoje),
                        ("state", "not in", ["encerrado"]),
                    ]
                ),
                "prazos_proximos": count(
                    [
                        ("prazo_resposta", ">=", hoje),
                        ("prazo_resposta", "<=", alerta_ate),
                        ("state", "not in", ["encerrado"]),
                    ]
                ),
                "urgentes_ativos": count(
                    [
                        ("urgencia", "=", True),
                        ("state", "not in", ["encerrado"]),
                    ]
                ),
                "retroativos_ativos": count(
                    [
                        ("retroativo", "=", True),
                        ("state", "not in", ["encerrado"]),
                    ]
                ),
            }

            processos_ativos = Processo.search(domain_base + [("state", "in", estados_ativos)])
            inertes = 0
            for processo in processos_ativos:
                ultimo = Tramite.search(
                    [("processo_id", "=", processo.id)],
                    order="date desc",
                    limit=1,
                )
                if not ultimo or ultimo.date < limite_inercia:
                    inertes += 1
            alertas["processos_inertes"] = inertes

            processos_fin = Processo.search(
                domain_base + [("state", "in", estados_ativos + ["demanda"])]
            )
            valor_total = sum(
                getattr(processo, "valor_total_estimado", 0.0) or 0.0 for processo in processos_fin
            )

            domain_doc = [("processo_id.ug_id", "=", ug_id)] if ug_id else []
            docs = {
                "em_revisao": Doc.search_count(domain_doc + [("state", "=", "revisao")]),
                "ia_pendentes": Doc.search_count(
                    domain_doc
                    + [("ai_generated", "=", True), ("state", "=", "revisao")]
                ),
            }

            mapa_inercia = []
            if not ug_id:
                for company in self.env["res.company"].search([]):
                    processos_ug = Processo.search(
                        [
                            ("ug_id", "=", company.id),
                            ("state", "in", estados_ativos),
                        ]
                    )
                    if not processos_ug:
                        continue
                    inertes_ug = 0
                    for processo in processos_ug:
                        ultimo = Tramite.search(
                            [("processo_id", "=", processo.id)],
                            order="date desc",
                            limit=1,
                        )
                        if not ultimo or ultimo.date < limite_inercia:
                            inertes_ug += 1
                    if inertes_ug > 0:
                        total_ug = len(processos_ug)
                        mapa_inercia.append(
                            {
                                "ug": company.name,
                                "ug_id": company.id,
                                "total": total_ug,
                                "inertes": inertes_ug,
                                "pct": round((inertes_ug / total_ug) * 100)
                                if total_ug
                                else 0,
                            }
                        )
                mapa_inercia.sort(key=lambda row: row["inertes"], reverse=True)
                mapa_inercia = mapa_inercia[:5]

            criticos = Processo.search(
                domain_base
                + [
                    "|",
                    ("prazo_vencido", "=", True),
                    "&",
                    ("urgencia", "=", True),
                    ("state", "not in", ["encerrado"]),
                ],
                order="prazo_resposta asc, id desc",
                limit=10,
            )
            lista_criticos = [
                {
                    "id": processo.id,
                    "name": processo.name,
                    "subject": processo.subject,
                    "state": processo.state,
                    "urgencia": processo.urgencia,
                    "prazo_vencido": processo.prazo_vencido,
                    "prazo_resposta": str(processo.prazo_resposta)
                    if processo.prazo_resposta
                    else "",
                    "responsible": processo.responsible_id.name
                    if processo.responsible_id
                    else "—",
                }
                for processo in criticos
            ]
            kpis["processos_criticos"] = len(lista_criticos)

            if Empenho is not None:
                domain_ne = [("state", "=", "emitido")]
                if ug_id:
                    domain_ne.append(("ug_id", "=", ug_id))
                empenhos = Empenho.search(domain_ne)
                kpis["total_empenhos"] = sum(
                    getattr(ne, "valor_liquido", 0.0) or 0.0 for ne in empenhos
                )

            if Liquidacao is not None:
                domain_nl = [("state", "=", "liquidado")]
                if ug_id:
                    domain_nl.append(("ug_id", "=", ug_id))
                liquidacoes = Liquidacao.search(domain_nl)
                kpis["total_liquidado"] = sum(
                    getattr(nl, "valor_liquidado", 0.0) or 0.0 for nl in liquidacoes
                )

            alertas_lista = []
            if alertas["prazos_vencidos"] > 0:
                alertas_lista.append(
                    {
                        "nivel": "critico",
                        "titulo": "Prazos vencidos",
                        "descricao": f"{alertas['prazos_vencidos']} processo(s) com prazo vencido.",
                    }
                )
            if alertas["prazos_proximos"] > 0:
                alertas_lista.append(
                    {
                        "nivel": "alto",
                        "titulo": "Vencimento em 7 dias",
                        "descricao": f"{alertas['prazos_proximos']} processo(s) vencendo em 7 dias.",
                    }
                )
            if alertas["processos_inertes"] > 0:
                alertas_lista.append(
                    {
                        "nivel": "medio",
                        "titulo": "Processos inertes",
                        "descricao": f"{alertas['processos_inertes']} processo(s) sem tramitação há mais de 21 dias.",
                    }
                )
            if alertas["urgentes_ativos"] > 0:
                alertas_lista.append(
                    {
                        "nivel": "alto",
                        "titulo": "Urgentes ativos",
                        "descricao": f"{alertas['urgentes_ativos']} processo(s) marcados como urgentes.",
                    }
                )

            return {
                "kpis": kpis,
                "alertas": alertas_lista,
                "alertas_kpis": alertas,
                "financeiro": {"valor_total": valor_total},
                "docs": docs,
                "mapa_inercia": mapa_inercia,
                "lista_criticos": lista_criticos,
                "contabil": self._get_dados_contabeis(ug_id=ug_id),
                "gerado_em": str(fields.Datetime.now()),
            }
        except Exception:
            # Never break the Owl dashboard: return a safe payload and log the traceback.
            _logger.exception("gov.dashboard: get_dashboard_data failed (ug_id=%s)", ug_id)
            return {
                "kpis": {
                    "total_processos": 0,
                    "total_ativos": 0,
                    "em_demanda": 0,
                    "em_instrucao": 0,
                    "em_planejamento": 0,
                    "em_licitacao": 0,
                    "em_contratacao": 0,
                    "em_execucao": 0,
                    "encerrados_mes": 0,
                    "processos_criticos": 0,
                    "total_empenhos": 0.0,
                    "total_liquidado": 0.0,
                },
                "alertas": [
                    {
                        "nivel": "critico",
                        "titulo": "Dashboard",
                        "descricao": "Falha ao carregar dados. Verifique logs do servidor.",
                    }
                ],
                "alertas_kpis": {
                    "prazos_vencidos": 0,
                    "prazos_proximos": 0,
                    "processos_inertes": 0,
                    "urgentes_ativos": 0,
                    "retroativos_ativos": 0,
                },
                "financeiro": {"valor_total": 0.0},
                "docs": {"em_revisao": 0, "ia_pendentes": 0},
                "mapa_inercia": [],
                "lista_criticos": [],
                "contabil": {
                    "configurado": False,
                    "saldo_por_conta": [],
                    "total_empenhado": 0.0,
                    "total_dotacao": 0.0,
                    "pct_executado": 0.0,
                    "alertas_estouro": [],
                    "moves_draft_count": 0,
                },
                "gerado_em": str(fields.Datetime.now()),
            }

    @api.model
    def _get_dados_contabeis(self, ug_id=None):
        """
        Retorna KPIs contábeis para o dashboard executivo.

        Graceful:
        - se modelos contábeis não estiverem disponíveis, retorna payload vazio.
        - se o usuário não tiver acesso aos modelos contábeis, retorna payload vazio.
        """
        resultado_vazio = {
            "configurado": False,
            "saldo_por_conta": [],
            "total_empenhado": 0.0,
            "total_dotacao": 0.0,
            "pct_executado": 0.0,
            "alertas_estouro": [],
            "moves_draft_count": 0,
        }

        # Avoid generating server-side AccessError logs for non-accounting users.
        # The dashboard should still load even if accounting KPIs are unavailable.
        def _has_any_group(xmlids):
            for xmlid in xmlids:
                try:
                    if self.env.user.has_group(xmlid):
                        return True
                except Exception:
                    continue
            return False

        if not _has_any_group(
            [
                "base.group_system",
                "account.group_account_manager",
                "account.group_account_invoice",
                "account.group_account_readonly",
            ]
        ):
            return resultado_vazio

        Config = self.env.get("gov.account.config")
        MoveLine = self.env.get("account.move.line")
        Move = self.env.get("account.move")
        Empenho = self.env.get("gov.empenho")
        Dotacao = self.env.get("gov.processo.dotacao")

        if Config is None or MoveLine is None or Move is None or Empenho is None:
            return resultado_vazio

        exercicio_atual = fields.Date.today().year
        inicio_ano = fields.Date.today().replace(month=1, day=1)

        domain_empenho = [
            ("state", "=", "emitido"),
            ("exercicio", "=", exercicio_atual),
        ]
        domain_dotacao = [("exercicio", "=", exercicio_atual)]
        domain_move_line = [
            ("move_id.state", "=", "posted"),
            ("move_id.date", ">=", inicio_ano),
        ]
        domain_draft = [
            ("state", "=", "draft"),
            ("move_type", "=", "entry"),
        ]

        if ug_id:
            domain_empenho.append(("ug_id", "=", ug_id))
            domain_dotacao.append(("processo_id.ug_id", "=", ug_id))
            domain_move_line.append(("company_id", "=", ug_id))
            domain_draft.append(("company_id", "=", ug_id))

        total_dotacao = 0.0
        if Dotacao is not None:
            dotacoes = Dotacao.search(domain_dotacao)
            total_dotacao = sum(dotacoes.mapped("valor_estimado"))

        nes = Empenho.search(domain_empenho)
        total_empenhado = sum(nes.mapped("valor_liquido"))

        try:
            domain_despesa = domain_move_line + [("account_id.account_type", "in", ["expense"])]
            linhas_despesa = MoveLine.search(domain_despesa)
        except AccessError:
            return resultado_vazio

        contas_dict = {}
        for linha in linhas_despesa:
            codigo = linha.account_id.code
            nome = linha.account_id.name
            if codigo not in contas_dict:
                contas_dict[codigo] = {
                    "codigo": codigo,
                    "nome": nome,
                    "empenhado": 0.0,
                    "estornado": 0.0,
                }
            contas_dict[codigo]["empenhado"] += linha.debit
            contas_dict[codigo]["estornado"] += linha.credit

        saldo_por_conta = []
        alertas_estouro = []
        for codigo, dados in sorted(contas_dict.items()):
            liquido = dados["empenhado"] - dados["estornado"]
            saldo_por_conta.append(
                {
                    "codigo": codigo,
                    "nome": dados["nome"],
                    "empenhado": dados["empenhado"],
                    "estornado": dados["estornado"],
                    "liquido": liquido,
                }
            )
            if liquido > total_dotacao > 0:
                alertas_estouro.append(
                    {
                        "conta": f"{codigo} - {dados['nome'][:40]}",
                        "empenhado": liquido,
                        "dotacao": total_dotacao,
                    }
                )

        pct_executado = 0.0
        if total_dotacao > 0:
            pct_executado = min(round((total_empenhado / total_dotacao) * 100, 1), 100.0)

        try:
            moves_draft_count = Move.search_count(domain_draft)
        except AccessError:
            moves_draft_count = 0

        return {
            "configurado": bool(Config.search_count([("active", "=", True)])),
            "saldo_por_conta": saldo_por_conta,
            "total_empenhado": total_empenhado,
            "total_dotacao": total_dotacao,
            "pct_executado": pct_executado,
            "alertas_estouro": alertas_estouro,
            "moves_draft_count": moves_draft_count,
        }
