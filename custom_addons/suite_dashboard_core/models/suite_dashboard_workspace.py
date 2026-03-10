import json

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError


class SuiteDashboardWorkspace(models.Model):
    _name = "suite.dashboard.workspace"
    _description = "Dashboard Workspace"
    _order = "sequence, id"

    name = fields.Char(required=True)
    owner_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    scope = fields.Selection(
        selection=[
            ("personal", "Personal"),
            ("team", "Team"),
            ("global", "Global"),
        ],
        required=True,
        default="personal",
    )
    company_ids = fields.Many2many(
        "res.company",
        "suite_dashboard_workspace_company_rel",
        "workspace_id",
        "company_id",
        string="Allowed Companies",
    )
    allowed_user_ids = fields.Many2many(
        "res.users",
        "suite_dashboard_workspace_allowed_user_rel",
        "workspace_id",
        "user_id",
        string="Team Users",
    )
    provider_key = fields.Char(required=True, index=True)
    template_id = fields.Many2one("suite.dashboard.template", ondelete="set null")
    default_date_filter = fields.Selection(
        selection=[
            ("today", "Today"),
            ("mtd", "Month to Date"),
            ("ytd", "Year to Date"),
            ("last_30", "Last 30 Days"),
            ("custom", "Custom"),
        ],
        default="mtd",
    )
    filter_state = fields.Text(default="{}")
    active = fields.Boolean(default=True)
    color = fields.Integer()
    sequence = fields.Integer(default=10)
    favorite_user_ids = fields.Many2many(
        "res.users",
        "suite_dashboard_workspace_favorite_user_rel",
        "workspace_id",
        "user_id",
        string="Favorite Users",
    )
    is_favorite = fields.Boolean(compute="_compute_is_favorite")
    item_ids = fields.One2many("suite.dashboard.workspace.item", "workspace_id", string="Items")

    @api.depends_context("uid")
    @api.depends("favorite_user_ids")
    def _compute_is_favorite(self):
        current_user_id = self.env.uid
        for rec in self:
            rec.is_favorite = current_user_id in rec.favorite_user_ids.ids

    def copy_data(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if "name" not in default:
            default["name"] = f"{self.name} (copy)"
        copied = super().copy_data(default=default)
        copied[0]["item_ids"] = [
            (
                0,
                0,
                {
                    "widget_key": item.widget_key,
                    "visible": item.visible,
                    "size": item.size,
                    "sequence": item.sequence,
                    "col_span": item.col_span,
                    "row_span": item.row_span,
                },
            )
            for item in self.item_ids
        ]
        return copied

    @api.model_create_multi
    def create(self, vals_list):
        templates = {}
        for vals in vals_list:
            template_id = vals.get("template_id")
            if not template_id:
                continue
            template = templates.get(template_id)
            if not template:
                template = self.env["suite.dashboard.template"].browse(template_id)
                templates[template_id] = template
            if template.exists():
                vals.setdefault("provider_key", template.provider_key)
                vals.setdefault("filter_state", template.default_filter_state or "{}")
                vals.setdefault("name", template.name)
        records = super().create(vals_list)
        for rec in records:
            rec._ensure_items_from_template()
        return records

    def write(self, vals):
        result = super().write(vals)
        for rec in self:
            if vals.get("template_id") and rec.template_id:
                if "provider_key" not in vals:
                    rec.provider_key = rec.template_id.provider_key
                if ("filter_state" not in vals or not vals.get("filter_state")) and rec.template_id.default_filter_state:
                    rec.filter_state = rec.template_id.default_filter_state
            if vals.get("template_id"):
                rec._ensure_items_from_template()
        return result

    def _ensure_items_from_template(self):
        for rec in self:
            if not rec.template_id:
                continue
            existing_keys = set(rec.item_ids.mapped("widget_key"))
            for definition in rec.template_id._get_item_definitions():
                widget_key = definition.get("widget_key")
                if not widget_key or widget_key in existing_keys:
                    continue
                rec.env["suite.dashboard.workspace.item"].create(
                    {
                        "workspace_id": rec.id,
                        "widget_key": widget_key,
                        "visible": definition.get("visible", True),
                        "size": definition.get("size", "md"),
                        "sequence": definition.get("sequence", 10),
                        "col_span": definition.get("col_span", 1),
                        "row_span": definition.get("row_span", 1),
                    }
                )

    def _json_loads(self, raw, fallback):
        if not raw:
            return fallback
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return fallback

    def _coerce_date(self, value, fallback):
        if not value:
            return fallback
        parsed = fields.Date.to_date(value)
        return parsed or fallback

    def _coerce_company_ids(self, company_ids):
        coerced_ids = []
        for company_id in company_ids or []:
            try:
                coerced_ids.append(int(company_id))
            except (TypeError, ValueError):
                continue
        allowed_ids = set(self.env.user.company_ids.ids)
        return [company_id for company_id in coerced_ids if company_id in allowed_ids]

    def _describe_date_filter(self, date_filter, date_from, date_to):
        if date_filter == "today":
            return "Hoje"
        if date_filter == "mtd":
            return "Mês até hoje"
        if date_filter == "ytd":
            return "Ano até hoje"
        if date_filter == "last_30":
            return "Últimos 30 dias"
        return f"{fields.Date.to_string(date_from)} -> {fields.Date.to_string(date_to)}"

    def _normalize_filters(self, filters=None):
        self.ensure_one()
        today = fields.Date.context_today(self)
        saved = self._json_loads(self.filter_state, {})
        runtime = filters or {}
        merged = dict(saved)
        merged.update(runtime)

        date_filter = merged.get("date_filter") or self.default_date_filter or "mtd"
        if date_filter == "today":
            date_from = date_to = today
        elif date_filter == "ytd":
            date_from = today.replace(month=1, day=1)
            date_to = today
        elif date_filter == "last_30":
            date_from = today - relativedelta(days=29)
            date_to = today
        elif date_filter == "custom":
            date_from = self._coerce_date(merged.get("date_from"), today.replace(day=1))
            date_to = self._coerce_date(merged.get("date_to"), today)
        else:
            date_from = today.replace(day=1)
            date_to = today

        if date_from > date_to:
            date_from, date_to = date_to, date_from

        company_ids = (
            self._coerce_company_ids(merged.get("company_ids"))
            or self.company_ids.ids
            or self.env.companies.ids
        )
        companies = self.env["res.company"].browse(company_ids)
        currency = companies[:1].currency_id or self.env.company.currency_id
        return {
            "date_filter": date_filter,
            "date_from": fields.Date.to_string(date_from),
            "date_to": fields.Date.to_string(date_to),
            "date_range_label": self._describe_date_filter(date_filter, date_from, date_to),
            "company_ids": companies.ids,
            "company_names": companies.mapped("name"),
            "is_multi_company": len(companies) > 1,
            "currency": {
                "name": currency.name,
                "symbol": currency.symbol,
                "position": currency.position,
            },
        }

    def _get_provider(self):
        self.ensure_one()
        registry = self.env["suite.dashboard.provider.registry"].search(
            [
                ("key", "=", self.provider_key),
                ("active", "=", True),
            ],
            limit=1,
        )
        if not registry:
            raise UserError(f"No active dashboard provider is registered for '{self.provider_key}'.")
        return self.env[registry.provider_model]

    def _check_dashboard_access(self):
        self.ensure_one()
        try:
            self.check_access("read")
        except AccessError as exc:
            raise AccessError("You do not have access to this dashboard workspace.") from exc

    def _serialize_switcher_workspaces(self):
        return [
            {
                "id": workspace.id,
                "name": workspace.name,
                "provider_key": workspace.provider_key,
                "scope": workspace.scope,
                "is_favorite": workspace.is_favorite,
                "default_date_filter": workspace.default_date_filter,
                "color": workspace.color,
            }
            for workspace in self.search([], order="sequence, name, id")
        ]

    def _serialize_company_options(self, selected_company_ids):
        selected_ids = set(selected_company_ids or [])
        return [
            {
                "id": company.id,
                "name": company.name,
                "selected": company.id in selected_ids,
            }
            for company in self.env.user.company_ids.sorted("name")
        ]

    def _build_workspace_meta(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "provider_key": self.provider_key,
            "scope": self.scope,
            "is_favorite": self.is_favorite,
            "owner_name": self.owner_id.name,
            "description": self.template_id.description or "",
            "template_code": self.template_id.code or False,
        }

    @api.model
    def get_default_dashboard_payload(self, filters=None):
        workspace = self.search([], order="sequence, id", limit=1)
        if not workspace:
            template = self.env["suite.dashboard.template"].search(
                [("active", "=", True)],
                order="sequence, id",
                limit=1,
            )
            if template:
                workspace = self.create(
                    {
                        "name": template.name,
                        "provider_key": template.provider_key,
                        "template_id": template.id,
                        "scope": "personal",
                    }
                )
            else:
                return {
                    "workspace": None,
                    "widgets": [],
                    "quick_access": [],
                    "available_workspaces": [],
                    "filters": {},
                    "message": "No dashboard templates are available yet.",
                }
        return workspace.get_dashboard_payload(filters)

    def get_dashboard_payload(self, filters=None):
        self.ensure_one()
        self._check_dashboard_access()
        self._ensure_items_from_template()

        normalized_filters = self._normalize_filters(filters)
        provider = self._get_provider()
        visible_items = self.item_ids.filtered("visible").sorted("sequence")
        widgets = []
        for item in visible_items:
            widget_payload = provider._get_widget_payload(item.widget_key, normalized_filters)
            if not widget_payload:
                continue
            drilldown_action = provider._get_drilldown_action(item.widget_key, normalized_filters)
            widget_payload.update(
                {
                    "widget_key": item.widget_key,
                    "drilldown_enabled": bool(drilldown_action),
                    "drilldown_action": drilldown_action or False,
                    "layout": {
                        "size": item.size,
                        "col_span": item.col_span,
                        "row_span": item.row_span,
                    },
                }
            )
            widgets.append(widget_payload)

        ai_context = provider._get_ai_context([item.widget_key for item in visible_items], normalized_filters)
        return {
            "workspace": self._build_workspace_meta(),
            "widgets": widgets,
            "quick_access": provider._get_quick_access_actions(normalized_filters),
            "ai_context": ai_context,
            "hero_metrics": (ai_context or {}).get("kpis", [])[:4],
            "filters": normalized_filters,
            "available_filters": {
                "date_filters": [
                    {"key": "today", "label": "Hoje"},
                    {"key": "mtd", "label": "MTD"},
                    {"key": "ytd", "label": "YTD"},
                    {"key": "last_30", "label": "30 dias"},
                    {"key": "custom", "label": "Custom"},
                ],
                "company_options": self._serialize_company_options(normalized_filters.get("company_ids")),
            },
            "available_workspaces": self._serialize_switcher_workspaces(),
            "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
        }

    def action_open_dashboard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "suite_dashboard_hub",
            "name": self.name,
            "params": {"workspace_id": self.id},
        }

    def action_open_hub(self):
        return self.action_open_dashboard()

    def toggle_favorite(self):
        current_user_id = self.env.uid
        for rec in self:
            favorite_rec = rec.sudo()
            if current_user_id in favorite_rec.favorite_user_ids.ids:
                favorite_rec.favorite_user_ids = [Command.unlink(current_user_id)]
            else:
                favorite_rec.favorite_user_ids = [Command.link(current_user_id)]
        self.invalidate_recordset(["favorite_user_ids", "is_favorite"])
        return True

    def action_toggle_favorite(self):
        return self.toggle_favorite()

    def action_duplicate_workspace(self):
        self.ensure_one()
        duplicate = self.copy({"owner_id": self.env.user.id, "scope": "personal"})
        return {
            "type": "ir.actions.act_window",
            "res_model": "suite.dashboard.workspace",
            "res_id": duplicate.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_snapshot(self, filters=None):
        self.ensure_one()
        snapshot = self.env["suite.dashboard.snapshot"].create(
            {
                "workspace_id": self.id,
                "filter_state": json.dumps(self._normalize_filters(filters), ensure_ascii=False),
            }
        )
        snapshot.action_generate_snapshot()
        return {
            "type": "ir.actions.act_window",
            "res_model": "suite.dashboard.snapshot",
            "res_id": snapshot.id,
            "view_mode": "form",
            "target": "current",
        }
