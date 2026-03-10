from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class SuiteDashboardProviderAccount(models.AbstractModel):
    _name = "suite.dashboard.provider.account"
    _inherit = "suite.dashboard.provider"
    _description = "Suite Dashboard Accounting Provider"

    def _get_widget_definitions(self):
        return [
            {"key": "acc_revenue_mtd", "label": "Receita", "type": "kpi"},
            {"key": "acc_expenses_mtd", "label": "Despesas", "type": "kpi"},
            {"key": "acc_net_result", "label": "Resultado", "type": "kpi"},
            {"key": "acc_cash_position", "label": "Caixa", "type": "kpi"},
            {"key": "acc_ar_overdue", "label": "Recebíveis vencidos", "type": "kpi"},
            {"key": "acc_ap_overdue", "label": "Pagáveis vencidos", "type": "kpi"},
            {"key": "acc_liquidity_pulse", "label": "Pulso de liquidez", "type": "chart"},
            {"key": "acc_revenue_trend", "label": "Momentum de receita", "type": "chart"},
            {"key": "acc_top_customers", "label": "Clientes líderes", "type": "table"},
        ]

    def _format_currency(self, amount, company_id=None):
        company = self.env["res.company"].browse(company_id) if company_id else self.env.company
        return format_currency_text(self.env, amount or 0.0, company.currency_id)

    def _company_id_from_filters(self, filters):
        return (filters.get("company_ids") or [self.env.company.id])[0]

    def _base_move_domain(self, filters):
        domain = [("state", "=", "posted")]
        if filters.get("date_from"):
            domain.append(("date", ">=", filters["date_from"]))
        if filters.get("date_to"):
            domain.append(("date", "<=", filters["date_to"]))
        if filters.get("company_ids"):
            domain.append(("company_id", "in", filters["company_ids"]))
        return domain

    def _invoice_domain(self, filters, move_types):
        domain = self._base_move_domain(filters)
        domain.append(("move_type", "in", list(move_types)))
        return domain

    def _signed_move_amount(self, move):
        sign = {
            "out_invoice": 1,
            "out_refund": -1,
            "in_invoice": 1,
            "in_refund": -1,
        }.get(move.move_type, 1)
        base_amount = abs(move.amount_total_signed or move.amount_total or 0.0)
        return sign * base_amount

    def _sum_moves(self, domain):
        moves = self.env["account.move"].search(domain)
        return sum(self._signed_move_amount(move) for move in moves)

    def _sum_overdue_lines(self, account_type, filters):
        domain = [
            ("move_id.state", "=", "posted"),
            ("account_type", "=", account_type),
            ("reconciled", "=", False),
            ("date_maturity", "!=", False),
            ("date_maturity", "<", filters.get("date_to") or fields.Date.context_today(self)),
        ]
        if filters.get("company_ids"):
            domain.append(("company_id", "in", filters["company_ids"]))
        lines = self.env["account.move.line"].search(domain)
        return sum(abs(line.amount_residual or 0.0) for line in lines)

    def _get_cash_position(self, filters):
        journals = self.env["account.journal"].search(
            [
                ("type", "in", ["bank", "cash"]),
                ("company_id", "in", filters.get("company_ids", self.env.companies.ids)),
            ]
        )
        return sum(
            journal.default_account_id.current_balance
            for journal in journals
            if journal.default_account_id
        )

    def _previous_period_filters(self, filters):
        date_from = fields.Date.to_date(filters.get("date_from")) or fields.Date.context_today(self)
        date_to = fields.Date.to_date(filters.get("date_to")) or fields.Date.context_today(self)
        delta_days = max((date_to - date_from).days, 0) + 1
        previous_to = date_from - relativedelta(days=1)
        previous_from = previous_to - relativedelta(days=delta_days - 1)
        return {
            **filters,
            "date_from": fields.Date.to_string(previous_from),
            "date_to": fields.Date.to_string(previous_to),
        }

    def _delta_pct(self, current_value, previous_value):
        if previous_value in (None, 0):
            return None
        return round(((current_value - previous_value) / abs(previous_value)) * 100, 1)

    def _get_metric_pack(self, filters):
        previous_filters = self._previous_period_filters(filters)
        revenue = self._sum_moves(self._invoice_domain(filters, ["out_invoice", "out_refund"]))
        expenses = self._sum_moves(self._invoice_domain(filters, ["in_invoice", "in_refund"]))
        previous_revenue = self._sum_moves(
            self._invoice_domain(previous_filters, ["out_invoice", "out_refund"])
        )
        previous_expenses = self._sum_moves(
            self._invoice_domain(previous_filters, ["in_invoice", "in_refund"])
        )
        ar_overdue = self._sum_overdue_lines("asset_receivable", filters)
        ap_overdue = self._sum_overdue_lines("liability_payable", filters)
        cash_position = self._get_cash_position(filters)

        metrics = {
            "revenue": revenue,
            "expenses": expenses,
            "net_result": revenue - expenses,
            "cash_position": cash_position,
            "ar_overdue": ar_overdue,
            "ap_overdue": ap_overdue,
            "previous_revenue": previous_revenue,
            "previous_expenses": previous_expenses,
            "previous_net_result": previous_revenue - previous_expenses,
            "previous_cash_position": None,
            "previous_ar_overdue": self._sum_overdue_lines("asset_receivable", previous_filters),
            "previous_ap_overdue": self._sum_overdue_lines("liability_payable", previous_filters),
        }
        metrics["cash_cover_pct"] = (
            round((cash_position / ap_overdue) * 100, 1) if ap_overdue else None
        )
        metrics["burn_gap"] = cash_position + ar_overdue - ap_overdue
        return metrics

    def _get_revenue_trend(self, filters):
        date_to = fields.Date.to_date(filters.get("date_to")) or fields.Date.context_today(self)
        start = date_to.replace(day=1) - relativedelta(months=11)
        invoices = self.env["account.move"].search(
            [
                ("state", "=", "posted"),
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("date", ">=", start),
                ("date", "<=", date_to),
                ("company_id", "in", filters.get("company_ids", self.env.companies.ids)),
            ]
        )

        amounts_by_month = defaultdict(float)
        for invoice in invoices:
            month_key = fields.Date.to_date(invoice.date).strftime("%Y-%m")
            amounts_by_month[month_key] += self._signed_move_amount(invoice)

        labels = []
        values = []
        cursor = start
        while cursor <= date_to:
            key = cursor.strftime("%Y-%m")
            labels.append(cursor.strftime("%b %Y"))
            values.append(round(amounts_by_month.get(key, 0.0), 2))
            cursor += relativedelta(months=1)
        return labels, values

    def _get_top_customers(self, filters):
        invoices = self.env["account.move"].search(self._invoice_domain(filters, ["out_invoice", "out_refund"]))
        amounts = defaultdict(float)
        partners = {}
        for invoice in invoices:
            partner = invoice.commercial_partner_id
            if not partner:
                continue
            partners[partner.id] = partner
            amounts[partner.id] += self._signed_move_amount(invoice)

        top_customers = [
            {
                "id": partner_id,
                "rank": index + 1,
                "name": partners[partner_id].name,
                "amount": round(total, 2),
            }
            for index, (partner_id, total) in enumerate(
                sorted(amounts.items(), key=lambda item: item[1], reverse=True)[:5]
            )
        ]
        return top_customers

    def _build_kpi(
        self,
        label,
        value,
        filters,
        subtitle=None,
        previous_value=None,
        accent_color="#0f766e",
        tone="neutral",
    ):
        company_id = self._company_id_from_filters(filters)
        return {
            "type": "kpi",
            "label": label,
            "value": round(value or 0.0, 2),
            "display_value": self._format_currency(value, company_id=company_id),
            "value_format": "currency",
            "subtitle": subtitle or "",
            "delta_pct": self._delta_pct(value, previous_value),
            "delta_label": "vs. per. anterior",
            "accent_color": accent_color,
            "tone": tone,
        }

    def _get_widget_payload(self, widget_key, filters):
        metrics = self._get_metric_pack(filters)

        if widget_key == "acc_revenue_mtd":
            return self._build_kpi(
                "Receita no período",
                metrics["revenue"],
                filters,
                "Faturas de cliente lançadas",
                previous_value=metrics["previous_revenue"],
                accent_color="#0f766e",
                tone="positive",
            )

        if widget_key == "acc_expenses_mtd":
            return self._build_kpi(
                "Despesas no período",
                metrics["expenses"],
                filters,
                "Contas de fornecedor lançadas",
                previous_value=metrics["previous_expenses"],
                accent_color="#f97316",
                tone="warning",
            )

        if widget_key == "acc_ar_overdue":
            return self._build_kpi(
                "Recebíveis vencidos",
                metrics["ar_overdue"],
                filters,
                "Valores em aberto acima do vencimento",
                previous_value=metrics["previous_ar_overdue"],
                accent_color="#d97706",
                tone="warning",
            )

        if widget_key == "acc_ap_overdue":
            return self._build_kpi(
                "Pagáveis vencidos",
                metrics["ap_overdue"],
                filters,
                "Obrigações vencidas ainda em aberto",
                previous_value=metrics["previous_ap_overdue"],
                accent_color="#dc2626",
                tone="negative",
            )

        if widget_key == "acc_cash_position":
            return self._build_kpi(
                "Posição de caixa",
                metrics["cash_position"],
                filters,
                "Saldo dos diários de banco e caixa",
                previous_value=metrics["previous_cash_position"],
                accent_color="#0284c7",
                tone="info",
            )

        if widget_key == "acc_net_result":
            return self._build_kpi(
                "Resultado líquido",
                metrics["net_result"],
                filters,
                "Receita líquida menos despesas",
                previous_value=metrics["previous_net_result"],
                accent_color="#2563eb",
                tone="positive" if metrics["net_result"] >= 0 else "negative",
            )

        if widget_key == "acc_revenue_trend":
            labels, values = self._get_revenue_trend(filters)
            return {
                "type": "chart",
                "label": "Momentum de receita",
                "subtitle": "Curva de 12 meses para leitura executiva",
                "summary": "Receita líquida mensal com devoluções já absorvidas.",
                "accent_color": "#0f766e",
                "chart": {
                    "type": "line",
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Receita líquida",
                            "data": values,
                            "fill": True,
                            "borderColor": "#0f766e",
                            "backgroundColor": "rgba(15, 118, 110, 0.16)",
                        }
                    ],
                },
            }

        if widget_key == "acc_top_customers":
            return {
                "type": "table",
                "label": "Clientes líderes",
                "subtitle": "Receita líquida no recorte selecionado",
                "summary": "Os parceiros mais relevantes para faturamento no período.",
                "columns": [
                    {"key": "rank", "label": "#", "type": "number"},
                    {"key": "name", "label": "Cliente", "type": "text"},
                    {"key": "amount", "label": "Receita", "type": "currency"},
                ],
                "rows": self._get_top_customers(filters),
                "accent_color": "#7c3aed",
            }

        if widget_key == "acc_liquidity_pulse":
            company_id = self._company_id_from_filters(filters)
            return {
                "type": "chart",
                "label": "Pulso de liquidez",
                "subtitle": "Cobertura imediata dos compromissos sensíveis",
                "summary": (
                    f"Caixa cobre {metrics['cash_cover_pct']:.1f}% do contas a pagar vencido."
                    if metrics["cash_cover_pct"] is not None
                    else "Sem contas a pagar vencidas no recorte."
                ),
                "accent_color": "#2563eb",
                "footer_note": (
                    f"Folga operacional: {self._format_currency(metrics['burn_gap'], company_id=company_id)}"
                ),
                "chart": {
                    "type": "bar",
                    "labels": ["Caixa", "AR vencido", "AP vencido"],
                    "datasets": [
                        {
                            "label": "Valor",
                            "data": [
                                round(metrics["cash_position"], 2),
                                round(metrics["ar_overdue"], 2),
                                round(metrics["ap_overdue"], 2),
                            ],
                            "backgroundColor": ["#0284c7", "#f59e0b", "#ef4444"],
                            "borderRadius": 12,
                        }
                    ],
                },
            }

        return None

    def _get_drilldown_action(self, widget_key, filters):
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        company_ids = filters.get("company_ids") or self.env.companies.ids

        move_base = [("company_id", "in", company_ids), ("state", "=", "posted")]
        if date_from:
            move_base.append(("date", ">=", date_from))
        if date_to:
            move_base.append(("date", "<=", date_to))

        if widget_key == "acc_revenue_mtd":
            return self._action_for_xmlid(
                "account.action_move_out_invoice_type",
                domain=move_base + [("move_type", "in", ["out_invoice", "out_refund"])],
                name="Receita do período",
            )
        if widget_key == "acc_expenses_mtd":
            return self._action_for_xmlid(
                "account.action_move_in_invoice_type",
                domain=move_base + [("move_type", "in", ["in_invoice", "in_refund"])],
                name="Despesas do período",
            )
        if widget_key == "acc_ar_overdue":
            return self._action_for_xmlid(
                "account.action_move_out_invoice_type",
                domain=move_base
                + [("invoice_date_due", "<", date_to), ("payment_state", "not in", ["paid", "in_payment"])],
                context={"search_default_late": 1, "search_default_posted": 1},
                name="Recebíveis vencidos",
            )
        if widget_key == "acc_ap_overdue":
            return self._action_for_xmlid(
                "account.action_move_in_invoice_type",
                domain=move_base
                + [("invoice_date_due", "<", date_to), ("payment_state", "not in", ["paid", "in_payment"])],
                context={"search_default_late": 1, "search_default_posted": 1},
                name="Pagáveis vencidos",
            )
        if widget_key == "acc_cash_position":
            return self._action_for_xmlid("account.action_account_journal_form", name="Diários de caixa e banco")
        if widget_key == "acc_net_result":
            action = self.env.ref("accounting_pdf_reports.action_account_report_pl", raise_if_not_found=False)
            if action:
                return self.env["ir.actions.actions"]._for_xml_id(
                    "accounting_pdf_reports.action_account_report_pl"
                )
            return self._action_for_xmlid(
                "account.action_move_journal_line",
                domain=move_base,
                name="Resultado líquido",
            )
        if widget_key == "acc_revenue_trend":
            return self._action_for_xmlid(
                "account.action_move_out_invoice_type",
                domain=move_base + [("move_type", "in", ["out_invoice", "out_refund"])],
                name="Receita dos últimos meses",
            )
        if widget_key == "acc_liquidity_pulse":
            return self._action_for_xmlid(
                "account.action_account_journal_form",
                name="Pulso de liquidez",
            )
        if widget_key == "acc_top_customers":
            partner_ids = [row["id"] for row in self._get_top_customers(filters)]
            return self._action_for_xmlid(
                "base.action_partner_customer_form",
                domain=[("id", "in", partner_ids)] if partner_ids else [("customer_rank", ">", 0)],
                name="Clientes líderes",
            )
        return False

    def _get_quick_access_actions(self, filters=None):
        return [
            {
                "key": "journal_entries",
                "label": "Lançamentos",
                "description": "Abrir os lançamentos contábeis do ambiente.",
                "accent_color": "#0f766e",
                "action": self._action_for_xmlid("account.action_move_journal_line"),
            },
            {
                "key": "customer_invoices",
                "label": "Faturas de cliente",
                "description": "Navegar no faturamento lançado e em aberto.",
                "accent_color": "#2563eb",
                "action": self._action_for_xmlid("account.action_move_out_invoice_type"),
            },
            {
                "key": "vendor_bills",
                "label": "Contas de fornecedor",
                "description": "Ir direto para despesas e obrigações do período.",
                "accent_color": "#f97316",
                "action": self._action_for_xmlid("account.action_move_in_invoice_type"),
            },
            {
                "key": "journals",
                "label": "Diários",
                "description": "Revisar bancos, caixa e estrutura operacional.",
                "accent_color": "#7c3aed",
                "action": self._action_for_xmlid("account.action_account_journal_form"),
            },
        ]

    def _get_ai_context(self, widget_keys, filters):
        metrics = self._get_metric_pack(filters)
        company_id = self._company_id_from_filters(filters)
        top_customers = self._get_top_customers(filters)
        lead_customer = top_customers[0]["name"] if top_customers else "sem concentração relevante"
        cash_cover = metrics["cash_cover_pct"]
        if cash_cover is None:
            liquidity_line = "Nenhum passivo vencido crítico apareceu neste recorte."
        elif cash_cover >= 100:
            liquidity_line = f"O caixa cobre {cash_cover:.1f}% do AP vencido, com pressão controlada."
        else:
            liquidity_line = f"O caixa cobre apenas {cash_cover:.1f}% do AP vencido e pede atenção imediata."
        return {
            "board": "Finance Command Center",
            "summary": (
                f"Receita líquida de {self._format_currency(metrics['revenue'], company_id=company_id)}, "
                f"despesas de {self._format_currency(metrics['expenses'], company_id=company_id)} "
                f"e resultado de {self._format_currency(metrics['net_result'], company_id=company_id)}. "
                f"{liquidity_line}"
            ),
            "highlights": [
                f"Cliente âncora do período: {lead_customer}.",
                f"Recebíveis vencidos em {self._format_currency(metrics['ar_overdue'], company_id=company_id)}.",
                f"Folga operacional atual: {self._format_currency(metrics['burn_gap'], company_id=company_id)}.",
            ],
            "period": {
                "from": filters.get("date_from"),
                "to": filters.get("date_to"),
            },
            "kpis": [
                {
                    "key": "acc_revenue_mtd",
                    "label": "Receita",
                    "value": metrics["revenue"],
                    "display_value": self._format_currency(metrics["revenue"], company_id=company_id),
                    "tone": "positive",
                },
                {
                    "key": "acc_net_result",
                    "label": "Resultado",
                    "value": metrics["net_result"],
                    "display_value": self._format_currency(metrics["net_result"], company_id=company_id),
                    "tone": "positive" if metrics["net_result"] >= 0 else "negative",
                },
                {
                    "key": "acc_cash_position",
                    "label": "Caixa",
                    "value": metrics["cash_position"],
                    "display_value": self._format_currency(
                        metrics["cash_position"], company_id=company_id
                    ),
                    "tone": "info",
                },
                {
                    "key": "acc_ap_overdue",
                    "label": "AP vencido",
                    "value": metrics["ap_overdue"],
                    "display_value": self._format_currency(metrics["ap_overdue"], company_id=company_id),
                    "tone": "negative",
                },
            ],
            "enabled_widgets": widget_keys,
        }


def format_currency_text(env, value, currency):
    html = env["ir.qweb.field.monetary"].value_to_html(
        value or 0.0,
        {
            "display_currency": currency,
            "from_currency": currency,
        },
    )
    return str(html).replace("<span>", "").replace("</span>", "")
