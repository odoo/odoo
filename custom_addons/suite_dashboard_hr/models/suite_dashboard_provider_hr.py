import pytz
from dateutil.relativedelta import relativedelta

from odoo import fields, models


class SuiteDashboardProviderHr(models.AbstractModel):
    _name = "suite.dashboard.provider.hr"
    _inherit = "suite.dashboard.provider"
    _description = "Suite Dashboard HR Provider"

    def _model_available(self, model_name):
        return bool(self.env.registry.get(model_name))

    def _get_widget_definitions(self):
        definitions = [
            {"key": "hr_headcount", "label": "Headcount", "type": "kpi"},
            {"key": "hr_dept_breakdown", "label": "Departments", "type": "chart"},
        ]
        optional = {
            "hr.leave": [
                {"key": "hr_leaves_pending", "label": "Pending Time Off", "type": "kpi"},
                {"key": "hr_leaves_today", "label": "People Away", "type": "kpi"},
            ],
            "hr.attendance": [
                {"key": "hr_attendance_late", "label": "Late Arrivals", "type": "kpi"},
            ],
            "hr.contract": [
                {"key": "hr_contracts_expiring", "label": "Contracts Expiring", "type": "table"},
            ],
            "hr.expense": [
                {"key": "hr_approvals_pending", "label": "Expense Approvals", "type": "kpi"},
            ],
        }
        for model_name, model_definitions in optional.items():
            if self._model_available(model_name):
                definitions.extend(model_definitions)
        return definitions

    def _format_number(self, value):
        return f"{int(round(value or 0)):,}".replace(",", ".")

    def _employee_domain(self, filters):
        domain = [("active", "=", True)]
        if filters.get("company_ids"):
            domain.append(("company_id", "in", filters["company_ids"]))
        return domain

    def _employee_count(self, filters):
        return self.env["hr.employee"].search_count(self._employee_domain(filters))

    def _department_breakdown(self, filters):
        rows = self.env["hr.employee"]._read_group(
            self._employee_domain(filters),
            ["department_id"],
            ["__count"],
        )
        labels = []
        values = []
        for department, count in rows:
            labels.append(department.display_name if department else "Sem departamento")
            values.append(count)
        if not labels:
            labels = ["Sem colaboradores"]
            values = [0]
        return labels, values

    def _leave_overlap_domain(self, filters, states):
        domain = [("state", "in", list(states))]
        if filters.get("company_ids"):
            domain.append(("employee_company_id", "in", filters["company_ids"]))
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        if date_from and date_to:
            domain.extend(
                [
                    ("request_date_from", "<=", date_to),
                    ("request_date_to", ">=", date_from),
                ]
            )
        return domain

    def _pending_leave_count(self, filters):
        if not self._model_available("hr.leave"):
            return None
        return self.env["hr.leave"].search_count(self._leave_overlap_domain(filters, ["confirm", "validate1"]))

    def _leave_today_count(self, filters):
        if not self._model_available("hr.leave"):
            return None
        anchor_date = fields.Date.to_date(filters.get("date_to")) or fields.Date.context_today(self)
        domain = [
            ("state", "=", "validate"),
            ("request_date_from", "<=", anchor_date),
            ("request_date_to", ">=", anchor_date),
        ]
        if filters.get("company_ids"):
            domain.append(("employee_company_id", "in", filters["company_ids"]))
        return self.env["hr.leave"].search_count(domain)

    def _expected_start_hour(self, attendance):
        calendar = attendance.employee_id.resource_calendar_id or attendance.employee_id.company_id.resource_calendar_id
        if not calendar or calendar.flexible_hours:
            return None
        dayofweek = str(attendance.date.weekday())
        attendances = calendar.attendance_ids.filtered(
            lambda line: line.dayofweek == dayofweek and line.day_period != "lunch"
        )
        if not attendances:
            return None
        return min(attendances.mapped("hour_from"))

    def _late_attendance_records(self, filters):
        if not self._model_available("hr.attendance"):
            return None
        anchor_date = fields.Date.to_date(filters.get("date_to")) or fields.Date.context_today(self)
        domain = [("date", "=", anchor_date)]
        if filters.get("company_ids"):
            domain.append(("employee_id.company_id", "in", filters["company_ids"]))
        attendances = self.env["hr.attendance"].search(domain)
        late_ids = []
        for attendance in attendances:
            if not attendance.check_in:
                continue
            expected_start = self._expected_start_hour(attendance)
            if expected_start is None:
                continue
            employee_tz = pytz.timezone(attendance.employee_id._get_tz())
            local_check_in = pytz.utc.localize(attendance.check_in).astimezone(employee_tz)
            actual_hour = (
                local_check_in.hour
                + (local_check_in.minute / 60.0)
                + (local_check_in.second / 3600.0)
            )
            if actual_hour > expected_start + 0.25:
                late_ids.append(attendance.id)
        return self.env["hr.attendance"].browse(late_ids)

    def _expense_pending_count(self, filters):
        if not self._model_available("hr.expense"):
            return None
        domain = [("state", "=", "submitted")]
        if filters.get("company_ids"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("date_from"):
            domain.append(("date", ">=", filters["date_from"]))
        if filters.get("date_to"):
            domain.append(("date", "<=", filters["date_to"]))
        return self.env["hr.expense"].search_count(domain)

    def _expiring_contract_rows(self, filters):
        if not self._model_available("hr.contract"):
            return []
        contract_model = self.env["hr.contract"]
        if "date_end" not in contract_model._fields:
            return []
        anchor_date = fields.Date.to_date(filters.get("date_to")) or fields.Date.context_today(self)
        limit_date = anchor_date + relativedelta(days=30)
        domain = [
            ("date_end", "!=", False),
            ("date_end", ">=", anchor_date),
            ("date_end", "<=", limit_date),
        ]
        if "company_id" in contract_model._fields and filters.get("company_ids"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if "state" in contract_model._fields:
            domain.append(("state", "not in", ["cancel", "close"]))
        contracts = contract_model.search(domain, limit=5, order="date_end asc")
        rows = []
        for index, contract in enumerate(contracts, start=1):
            rows.append(
                {
                    "rank": index,
                    "employee": contract.employee_id.name or contract.display_name,
                    "date_end": fields.Date.to_string(contract.date_end),
                }
            )
        return rows

    def _build_kpi(self, label, value, subtitle, accent_color, tone):
        return {
            "type": "kpi",
            "label": label,
            "value": int(value or 0),
            "display_value": self._format_number(value),
            "value_format": "number",
            "subtitle": subtitle,
            "accent_color": accent_color,
            "tone": tone,
        }

    def _get_widget_payload(self, widget_key, filters):
        if widget_key == "hr_headcount":
            count = self._employee_count(filters)
            return self._build_kpi(
                "Headcount ativo",
                count,
                "Colaboradores ativos no perímetro filtrado",
                "#0f766e",
                "positive",
            )

        if widget_key == "hr_dept_breakdown":
            labels, values = self._department_breakdown(filters)
            top_department = ""
            if values and any(values):
                leader = max(zip(labels, values), key=lambda item: item[1])
                top_department = f"Maior núcleo: {leader[0]} ({leader[1]})."
            return {
                "type": "chart",
                "label": "Distribuição por departamento",
                "subtitle": "Mix atual de equipes ativas",
                "summary": top_department or "Ainda não há colaboradores suficientes para distribuir por área.",
                "accent_color": "#2563eb",
                "chart": {
                    "type": "doughnut",
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Colaboradores",
                            "data": values,
                            "backgroundColor": [
                                "#2563eb",
                                "#7c3aed",
                                "#0f766e",
                                "#f97316",
                                "#dc2626",
                                "#14b8a6",
                            ],
                            "borderWidth": 0,
                        }
                    ],
                },
            }

        if widget_key == "hr_leaves_pending":
            count = self._pending_leave_count(filters)
            if count is None:
                return None
            return self._build_kpi(
                "Time Off pendente",
                count,
                "Solicitações aguardando ação gerencial",
                "#f59e0b",
                "warning",
            )

        if widget_key == "hr_leaves_today":
            count = self._leave_today_count(filters)
            if count is None:
                return None
            return self._build_kpi(
                "Ausentes na data-base",
                count,
                "Colaboradores aprovados para a data final do filtro",
                "#7c3aed",
                "info",
            )

        if widget_key == "hr_attendance_late":
            if not self._model_available("hr.attendance"):
                return None
            late_records = self._late_attendance_records(filters) or self.env["hr.attendance"]
            late_count = len(late_records)
            return self._build_kpi(
                "Chegadas tardias",
                late_count,
                "Check-ins com mais de 15 min após o início esperado",
                "#dc2626",
                "negative" if late_count else "positive",
            )

        if widget_key == "hr_approvals_pending":
            count = self._expense_pending_count(filters)
            if count is None:
                return None
            return self._build_kpi(
                "Despesas para aprovar",
                count,
                "Fluxo financeiro de RH esperando conferência",
                "#f97316",
                "warning",
            )

        if widget_key == "hr_contracts_expiring":
            rows = self._expiring_contract_rows(filters)
            if not rows:
                return None
            return {
                "type": "table",
                "label": "Contratos expirando",
                "subtitle": "Próximos 30 dias a partir da data-base",
                "summary": "Renovações que merecem alinhamento antecipado.",
                "columns": [
                    {"key": "rank", "label": "#", "type": "number"},
                    {"key": "employee", "label": "Colaborador", "type": "text"},
                    {"key": "date_end", "label": "Fim", "type": "text"},
                ],
                "rows": rows,
                "accent_color": "#0ea5e9",
            }

        return None

    def _get_drilldown_action(self, widget_key, filters):
        if widget_key == "hr_headcount":
            return self._action_for_xmlid(
                "hr.open_view_employee_list",
                domain=self._employee_domain(filters),
                name="Headcount ativo",
            )

        if widget_key == "hr_dept_breakdown":
            return self._action_for_xmlid(
                "hr.open_view_employee_list",
                domain=self._employee_domain(filters),
                context={"group_by": "department_id"},
                name="Colaboradores por departamento",
            )

        if widget_key == "hr_leaves_pending" and self._model_available("hr.leave"):
            return self._action_for_xmlid(
                "hr_holidays.hr_leave_action_action_approve_department",
                domain=self._leave_overlap_domain(filters, ["confirm", "validate1"]),
                context={
                    "search_default_waiting_for_me": 0,
                    "search_default_waiting_for_me_manager": 0,
                    "search_default_current_year": 0,
                    "hide_employee_name": 1,
                },
                name="Time Off pendente",
            )

        if widget_key == "hr_leaves_today" and self._model_available("hr.leave"):
            anchor_date = fields.Date.to_date(filters.get("date_to")) or fields.Date.context_today(self)
            domain = [
                ("state", "=", "validate"),
                ("request_date_from", "<=", anchor_date),
                ("request_date_to", ">=", anchor_date),
            ]
            if filters.get("company_ids"):
                domain.append(("employee_company_id", "in", filters["company_ids"]))
            return self._action_for_xmlid(
                "hr_holidays.hr_leave_action_action_approve_department",
                domain=domain,
                context={
                    "search_default_waiting_for_me": 0,
                    "search_default_waiting_for_me_manager": 0,
                    "search_default_current_year": 0,
                    "hide_employee_name": 1,
                },
                name="Ausentes na data-base",
            )

        if widget_key == "hr_attendance_late" and self._model_available("hr.attendance"):
            late_records = self._late_attendance_records(filters) or self.env["hr.attendance"]
            return self._action_for_xmlid(
                "hr_attendance.hr_attendance_management_action",
                domain=[("id", "in", late_records.ids)] if late_records else [("id", "=", 0)],
                name="Chegadas tardias",
            )

        if widget_key == "hr_approvals_pending" and self._model_available("hr.expense"):
            domain = [("state", "=", "submitted")]
            if filters.get("company_ids"):
                domain.append(("company_id", "in", filters["company_ids"]))
            if filters.get("date_from"):
                domain.append(("date", ">=", filters["date_from"]))
            if filters.get("date_to"):
                domain.append(("date", "<=", filters["date_to"]))
            return self._action_for_xmlid(
                "hr_expense.hr_expense_actions_to_process",
                domain=domain,
                name="Despesas para aprovar",
            )

        if widget_key == "hr_contracts_expiring" and self._model_available("hr.contract"):
            contract_model = self.env["hr.contract"]
            if "date_end" not in contract_model._fields:
                return False
            anchor_date = fields.Date.to_date(filters.get("date_to")) or fields.Date.context_today(self)
            limit_date = anchor_date + relativedelta(days=30)
            domain = [
                ("date_end", "!=", False),
                ("date_end", ">=", anchor_date),
                ("date_end", "<=", limit_date),
            ]
            if "company_id" in contract_model._fields and filters.get("company_ids"):
                domain.append(("company_id", "in", filters["company_ids"]))
            return {
                "type": "ir.actions.act_window",
                "name": "Contratos expirando",
                "res_model": "hr.contract",
                "view_mode": "list,form",
                "domain": domain,
                "target": "current",
            }

        return False

    def _get_quick_access_actions(self, filters=None):
        filters = filters or {}
        items = [
            {
                "key": "employees",
                "label": "Colaboradores",
                "description": "Abrir a base ativa de pessoas e movimentos.",
                "accent_color": "#0f766e",
                "action": self._action_for_xmlid(
                    "hr.open_view_employee_list",
                    domain=self._employee_domain(filters),
                ),
            },
            {
                "key": "departments",
                "label": "Departamentos",
                "description": "Revisar a estrutura organizacional e gestores.",
                "accent_color": "#2563eb",
                "action": self._action_for_xmlid("hr.hr_department_tree_action"),
            },
        ]
        if self._model_available("hr.leave"):
            items.append(
                {
                    "key": "time_off",
                    "label": "Time Off",
                    "description": "Ir direto para a fila de aprovações e ausências.",
                    "accent_color": "#7c3aed",
                    "action": self._action_for_xmlid("hr_holidays.hr_leave_action_action_approve_department"),
                }
            )
        if self._model_available("hr.attendance"):
            items.append(
                {
                    "key": "attendance",
                    "label": "Presenças",
                    "description": "Acompanhar check-ins, jornada e desvios de rotina.",
                    "accent_color": "#dc2626",
                    "action": self._action_for_xmlid("hr_attendance.hr_attendance_management_action"),
                }
            )
        if self._model_available("hr.expense"):
            items.append(
                {
                    "key": "expenses",
                    "label": "Despesas",
                    "description": "Atalhar o fluxo de conferência e aprovação.",
                    "accent_color": "#f97316",
                    "action": self._action_for_xmlid("hr_expense.hr_expense_actions_to_process"),
                }
            )
        return [item for item in items if item["action"]]

    def _get_ai_context(self, widget_keys, filters):
        headcount = self._employee_count(filters)
        department_labels, department_values = self._department_breakdown(filters)
        department_count = len([value for value in department_values if value])
        leave_pending = self._pending_leave_count(filters)
        leave_today = self._leave_today_count(filters)
        late_count = None
        if self._model_available("hr.attendance"):
            late_count = len(self._late_attendance_records(filters) or self.env["hr.attendance"])
        expense_pending = self._expense_pending_count(filters)

        highlights = []
        if department_count:
            lead_department = max(zip(department_labels, department_values), key=lambda item: item[1])
            highlights.append(f"Maior time atual: {lead_department[0]} com {lead_department[1]} pessoas.")
        if leave_pending is not None:
            highlights.append(f"Fila de time off em aberto: {self._format_number(leave_pending)}.")
        if expense_pending is not None:
            highlights.append(f"Despesas aguardando decisão: {self._format_number(expense_pending)}.")
        if late_count is not None:
            highlights.append(f"Chegadas tardias no recorte diário: {self._format_number(late_count)}.")

        summary_bits = [
            f"Headcount ativo em {self._format_number(headcount)} colaboradores.",
            f"Estrutura distribuída em {self._format_number(department_count)} frentes com pessoas ativas."
            if department_count
            else "Ainda não há distribuição relevante por departamentos.",
        ]
        if leave_today is not None:
            summary_bits.append(
                f"{self._format_number(leave_today)} pessoas estão ausentes na data-base do dashboard."
            )

        kpis = [
            {
                "key": "hr_headcount",
                "label": "Headcount",
                "value": headcount,
                "display_value": self._format_number(headcount),
                "tone": "positive",
            },
            {
                "key": "hr_dept_breakdown",
                "label": "Departamentos",
                "value": department_count,
                "display_value": self._format_number(department_count),
                "tone": "info",
            },
        ]
        if leave_pending is not None:
            kpis.append(
                {
                    "key": "hr_leaves_pending",
                    "label": "Pendências",
                    "value": leave_pending,
                    "display_value": self._format_number(leave_pending),
                    "tone": "warning",
                }
            )
        if late_count is not None:
            kpis.append(
                {
                    "key": "hr_attendance_late",
                    "label": "Atrasos",
                    "value": late_count,
                    "display_value": self._format_number(late_count),
                    "tone": "negative" if late_count else "positive",
                }
            )

        return {
            "board": "People Command Center",
            "summary": " ".join(summary_bits),
            "highlights": highlights,
            "period": {
                "from": filters.get("date_from"),
                "to": filters.get("date_to"),
            },
            "kpis": kpis,
            "enabled_widgets": widget_keys,
        }
