from collections import defaultdict
from datetime import datetime, time

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class SuiteDashboardProviderSales(models.AbstractModel):
    _name = "suite.dashboard.provider.sales"
    _inherit = "suite.dashboard.provider"
    _description = "Suite Dashboard Sales Provider"

    def _get_widget_definitions(self):
        return [
            {"key": "sale_booked_revenue", "label": "Booked Revenue", "type": "kpi"},
            {"key": "sale_orders_confirmed", "label": "Confirmed Orders", "type": "kpi"},
            {"key": "sale_quotes_open", "label": "Open Quotations", "type": "kpi"},
            {"key": "sale_to_invoice", "label": "To Invoice", "type": "kpi"},
            {"key": "sale_avg_ticket", "label": "Average Ticket", "type": "kpi"},
            {"key": "sale_conversion_rate", "label": "Conversion", "type": "kpi"},
            {"key": "sale_revenue_trend", "label": "Revenue Trend", "type": "chart"},
            {"key": "sale_salesperson_mix", "label": "Salespeople", "type": "chart"},
            {"key": "sale_top_customers", "label": "Top Customers", "type": "table"},
        ]

    def _format_currency(self, amount, company_id=None):
        company = self.env["res.company"].browse(company_id) if company_id else self.env.company
        return format_currency_text(self.env, amount or 0.0, company.currency_id)

    def _company_id_from_filters(self, filters):
        return (filters.get("company_ids") or [self.env.company.id])[0]

    def _datetime_bounds(self, filters):
        date_from = fields.Date.to_date(filters.get("date_from")) or fields.Date.context_today(self)
        date_to = fields.Date.to_date(filters.get("date_to")) or fields.Date.context_today(self)
        start = fields.Datetime.to_string(datetime.combine(date_from, time.min))
        end = fields.Datetime.to_string(datetime.combine(date_to, time.max))
        return start, end

    def _base_order_domain(self, filters, states=None):
        start, end = self._datetime_bounds(filters)
        domain = [
            ("date_order", ">=", start),
            ("date_order", "<=", end),
        ]
        if filters.get("company_ids"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if states:
            domain.append(("state", "in", list(states)))
        return domain

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

    def _sum_amount(self, domain):
        return sum(self.env["sale.order"].search(domain).mapped("amount_total"))

    def _count_orders(self, domain):
        return self.env["sale.order"].search_count(domain)

    def _get_metrics(self, filters):
        confirmed_states = ["sale", "done"]
        open_quote_states = ["draft", "sent"]
        previous_filters = self._previous_period_filters(filters)

        booked_revenue = self._sum_amount(self._base_order_domain(filters, confirmed_states))
        previous_booked = self._sum_amount(self._base_order_domain(previous_filters, confirmed_states))
        confirmed_orders = self._count_orders(self._base_order_domain(filters, confirmed_states))
        previous_confirmed = self._count_orders(self._base_order_domain(previous_filters, confirmed_states))
        open_quotes = self._count_orders(self._base_order_domain(filters, open_quote_states))
        previous_quotes = self._count_orders(self._base_order_domain(previous_filters, open_quote_states))
        to_invoice = self._count_orders(
            self._base_order_domain(filters, confirmed_states) + [("invoice_status", "=", "to invoice")]
        )
        previous_to_invoice = self._count_orders(
            self._base_order_domain(previous_filters, confirmed_states) + [("invoice_status", "=", "to invoice")]
        )
        avg_ticket = round(booked_revenue / confirmed_orders, 2) if confirmed_orders else 0.0
        previous_avg_ticket = round(previous_booked / previous_confirmed, 2) if previous_confirmed else 0.0
        total_pipeline = confirmed_orders + open_quotes
        previous_pipeline = previous_confirmed + previous_quotes
        conversion_rate = round((confirmed_orders / total_pipeline) * 100, 1) if total_pipeline else 0.0
        previous_conversion = (
            round((previous_confirmed / previous_pipeline) * 100, 1) if previous_pipeline else 0.0
        )
        return {
            "booked_revenue": booked_revenue,
            "previous_booked_revenue": previous_booked,
            "confirmed_orders": confirmed_orders,
            "previous_confirmed_orders": previous_confirmed,
            "open_quotes": open_quotes,
            "previous_open_quotes": previous_quotes,
            "to_invoice": to_invoice,
            "previous_to_invoice": previous_to_invoice,
            "avg_ticket": avg_ticket,
            "previous_avg_ticket": previous_avg_ticket,
            "conversion_rate": conversion_rate,
            "previous_conversion_rate": previous_conversion,
        }

    def _revenue_trend(self, filters):
        date_to = fields.Date.to_date(filters.get("date_to")) or fields.Date.context_today(self)
        start = date_to.replace(day=1) - relativedelta(months=11)
        orders = self.env["sale.order"].search(
            self._base_order_domain(
                {
                    **filters,
                    "date_from": fields.Date.to_string(start),
                    "date_to": filters.get("date_to") or fields.Date.to_string(date_to),
                },
                ["sale", "done"],
            )
        )
        amounts_by_month = defaultdict(float)
        for order in orders:
            month_key = fields.Date.to_date(order.date_order.date()).strftime("%Y-%m")
            amounts_by_month[month_key] += order.amount_total

        labels = []
        values = []
        cursor = start
        while cursor <= date_to:
            key = cursor.strftime("%Y-%m")
            labels.append(cursor.strftime("%b %Y"))
            values.append(round(amounts_by_month.get(key, 0.0), 2))
            cursor += relativedelta(months=1)
        return labels, values

    def _salesperson_mix(self, filters):
        rows = self.env["sale.order"]._read_group(
            self._base_order_domain(filters, ["sale", "done"]),
            ["user_id"],
            ["amount_total:sum"],
        )
        labels = []
        values = []
        for user, amount_total in rows:
            labels.append(user.display_name if user else "Sem vendedor")
            values.append(round(amount_total or 0.0, 2))
        if not labels:
            labels = ["Sem vendas"]
            values = [0.0]
        return labels[:6], values[:6]

    def _top_customers(self, filters):
        rows = self.env["sale.order"]._read_group(
            self._base_order_domain(filters, ["sale", "done"]),
            ["partner_id"],
            ["amount_total:sum"],
        )
        top_rows = []
        for partner, amount_total in sorted(rows, key=lambda row: row[1] or 0.0, reverse=True)[:5]:
            top_rows.append(
                {
                    "id": partner.id if partner else False,
                    "rank": len(top_rows) + 1,
                    "name": partner.display_name if partner else "Cliente não definido",
                    "amount": round(amount_total or 0.0, 2),
                }
            )
        return top_rows

    def _build_kpi(
        self,
        label,
        value,
        filters,
        subtitle,
        previous_value=None,
        accent_color="#2563eb",
        tone="neutral",
        value_format="number",
    ):
        company_id = self._company_id_from_filters(filters)
        display_value = (
            self._format_currency(value, company_id=company_id)
            if value_format == "currency"
            else f"{value:.1f}%" if value_format == "percentage"
            else format_number(value)
        )
        return {
            "type": "kpi",
            "label": label,
            "value": round(value or 0.0, 2),
            "display_value": display_value,
            "value_format": value_format,
            "subtitle": subtitle,
            "delta_pct": self._delta_pct(value, previous_value),
            "delta_label": "vs. per. anterior",
            "accent_color": accent_color,
            "tone": tone,
        }

    def _get_widget_payload(self, widget_key, filters):
        metrics = self._get_metrics(filters)

        if widget_key == "sale_booked_revenue":
            return self._build_kpi(
                "Receita fechada",
                metrics["booked_revenue"],
                filters,
                "Pedidos confirmados no recorte",
                previous_value=metrics["previous_booked_revenue"],
                accent_color="#0f766e",
                tone="positive",
                value_format="currency",
            )
        if widget_key == "sale_orders_confirmed":
            return self._build_kpi(
                "Pedidos confirmados",
                metrics["confirmed_orders"],
                filters,
                "Pedidos em venda ou concluídos",
                previous_value=metrics["previous_confirmed_orders"],
                accent_color="#2563eb",
                tone="info",
            )
        if widget_key == "sale_quotes_open":
            return self._build_kpi(
                "Cotações abertas",
                metrics["open_quotes"],
                filters,
                "Oportunidades ainda em composição",
                previous_value=metrics["previous_open_quotes"],
                accent_color="#7c3aed",
                tone="warning",
            )
        if widget_key == "sale_to_invoice":
            return self._build_kpi(
                "Pedidos a faturar",
                metrics["to_invoice"],
                filters,
                "Carteira pronta para avançar ao financeiro",
                previous_value=metrics["previous_to_invoice"],
                accent_color="#f97316",
                tone="warning",
            )
        if widget_key == "sale_avg_ticket":
            return self._build_kpi(
                "Ticket médio",
                metrics["avg_ticket"],
                filters,
                "Receita média por pedido confirmado",
                previous_value=metrics["previous_avg_ticket"],
                accent_color="#0891b2",
                tone="info",
                value_format="currency",
            )
        if widget_key == "sale_conversion_rate":
            return self._build_kpi(
                "Conversão",
                metrics["conversion_rate"],
                filters,
                "Pedidos confirmados sobre o pipeline do período",
                previous_value=metrics["previous_conversion_rate"],
                accent_color="#dc2626",
                tone="positive" if metrics["conversion_rate"] >= 50 else "warning",
                value_format="percentage",
            )
        if widget_key == "sale_revenue_trend":
            labels, values = self._revenue_trend(filters)
            return {
                "type": "chart",
                "label": "Momentum comercial",
                "subtitle": "Receita confirmada dos últimos 12 meses",
                "summary": "Leitura executiva para sazonalidade e aceleração do comercial.",
                "accent_color": "#0f766e",
                "chart": {
                    "type": "line",
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Receita confirmada",
                            "data": values,
                            "fill": True,
                            "borderColor": "#0f766e",
                            "backgroundColor": "rgba(15, 118, 110, 0.16)",
                        }
                    ],
                },
            }
        if widget_key == "sale_salesperson_mix":
            labels, values = self._salesperson_mix(filters)
            return {
                "type": "chart",
                "label": "Mix por vendedor",
                "subtitle": "Quem está puxando a receita confirmada",
                "summary": "Distribuição da carteira fechada por responsável comercial.",
                "accent_color": "#2563eb",
                "chart": {
                    "type": "bar",
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Receita",
                            "data": values,
                            "backgroundColor": ["#2563eb", "#0f766e", "#7c3aed", "#f97316", "#dc2626", "#0891b2"],
                            "borderRadius": 12,
                        }
                    ],
                },
            }
        if widget_key == "sale_top_customers":
            return {
                "type": "table",
                "label": "Clientes líderes",
                "subtitle": "Top 5 por receita confirmada",
                "summary": "Concentração comercial do período selecionado.",
                "columns": [
                    {"key": "rank", "label": "#", "type": "number"},
                    {"key": "name", "label": "Cliente", "type": "text"},
                    {"key": "amount", "label": "Receita", "type": "currency"},
                ],
                "rows": self._top_customers(filters),
                "accent_color": "#7c3aed",
            }
        return None

    def _get_drilldown_action(self, widget_key, filters):
        confirmed_domain = self._base_order_domain(filters, ["sale", "done"])
        quotation_domain = self._base_order_domain(filters, ["draft", "sent"])
        pipeline_domain = self._base_order_domain(filters, ["draft", "sent", "sale", "done"])

        if widget_key in {"sale_booked_revenue", "sale_orders_confirmed", "sale_avg_ticket"}:
            return self._action_for_xmlid(
                "sale.action_orders",
                domain=confirmed_domain,
                name="Pedidos confirmados",
            )
        if widget_key == "sale_quotes_open":
            return self._action_for_xmlid(
                "sale.action_quotations",
                domain=quotation_domain,
                name="Cotações abertas",
            )
        if widget_key == "sale_to_invoice":
            return self._action_for_xmlid(
                "sale.action_orders_to_invoice",
                domain=confirmed_domain + [("invoice_status", "=", "to invoice")],
                name="Pedidos a faturar",
            )
        if widget_key == "sale_conversion_rate":
            return self._action_for_xmlid(
                "sale.action_quotations",
                domain=pipeline_domain,
                name="Pipeline comercial",
            )
        if widget_key == "sale_revenue_trend":
            return self._action_for_xmlid(
                "sale.action_orders",
                domain=confirmed_domain,
                name="Receita confirmada",
            )
        if widget_key == "sale_salesperson_mix":
            return self._action_for_xmlid(
                "sale.action_orders",
                domain=confirmed_domain,
                context={"group_by": "user_id"},
                name="Receita por vendedor",
            )
        if widget_key == "sale_top_customers":
            partner_ids = [row["id"] for row in self._top_customers(filters) if row.get("id")]
            return self._action_for_xmlid(
                "base.action_partner_customer_form",
                domain=[("id", "in", partner_ids)] if partner_ids else [("customer_rank", ">", 0)],
                name="Clientes líderes",
            )
        return False

    def _get_quick_access_actions(self, filters=None):
        return [
            {
                "key": "quotations",
                "label": "Cotações",
                "description": "Abrir o funil em proposta e negociação.",
                "accent_color": "#7c3aed",
                "action": self._action_for_xmlid("sale.action_quotations"),
            },
            {
                "key": "orders",
                "label": "Pedidos",
                "description": "Navegar nos pedidos já confirmados.",
                "accent_color": "#0f766e",
                "action": self._action_for_xmlid("sale.action_orders"),
            },
            {
                "key": "to_invoice",
                "label": "A faturar",
                "description": "Atalhar a carteira pronta para faturamento.",
                "accent_color": "#f97316",
                "action": self._action_for_xmlid("sale.action_orders_to_invoice"),
            },
        ]

    def _get_ai_context(self, widget_keys, filters):
        metrics = self._get_metrics(filters)
        company_id = self._company_id_from_filters(filters)
        top_customers = self._top_customers(filters)
        lead_customer = top_customers[0]["name"] if top_customers else "sem concentração relevante"
        return {
            "board": "Sales Command Center",
            "summary": (
                f"Receita fechada de {self._format_currency(metrics['booked_revenue'], company_id=company_id)}, "
                f"{format_number(metrics['confirmed_orders'])} pedidos confirmados e "
                f"{metrics['conversion_rate']:.1f}% de conversão no recorte."
            ),
            "highlights": [
                f"Cotações abertas: {format_number(metrics['open_quotes'])}.",
                f"Pedidos a faturar: {format_number(metrics['to_invoice'])}.",
                f"Cliente âncora do período: {lead_customer}.",
            ],
            "period": {
                "from": filters.get("date_from"),
                "to": filters.get("date_to"),
            },
            "kpis": [
                {
                    "key": "sale_booked_revenue",
                    "label": "Receita",
                    "value": metrics["booked_revenue"],
                    "display_value": self._format_currency(metrics["booked_revenue"], company_id=company_id),
                    "tone": "positive",
                },
                {
                    "key": "sale_orders_confirmed",
                    "label": "Pedidos",
                    "value": metrics["confirmed_orders"],
                    "display_value": format_number(metrics["confirmed_orders"]),
                    "tone": "info",
                },
                {
                    "key": "sale_quotes_open",
                    "label": "Cotações",
                    "value": metrics["open_quotes"],
                    "display_value": format_number(metrics["open_quotes"]),
                    "tone": "warning",
                },
                {
                    "key": "sale_conversion_rate",
                    "label": "Conversão",
                    "value": metrics["conversion_rate"],
                    "display_value": f"{metrics['conversion_rate']:.1f}%",
                    "tone": "positive" if metrics["conversion_rate"] >= 50 else "warning",
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


def format_number(value):
    return f"{int(round(value or 0)):,}".replace(",", ".")
