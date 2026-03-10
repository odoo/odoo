from odoo import models, fields, api, _
from markupsafe import Markup
from odoo.exceptions import ValidationError


class Dashboard(models.Model):
    _name = "dashboard.dashboard"
    _description = "Dashboard"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def _compute_chart_count(self):
        for dashboard in self:
            dashboard.chart_count = len(dashboard.chart_ids)

    name = fields.Char(string="Name", required=True, tracking=True)
    chart_count = fields.Integer(string="Chart Count", compute="_compute_chart_count")
    chart_ids = fields.One2many(
        "dashboard.chart", "dashboard_id", string="Charts", copy=False
    )
    parent_menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Parent Menu",
        default=lambda self: self.env.ref(
            "synconics_bi_dashboard.parent_dashboard_menu"
        ),
        domain=[("action", "=", False)],
        tracking=True,
    )
    created_menu_id = fields.Many2one(
        "ir.ui.menu", string="Menu", copy=False, tracking=True
    )
    created_action_id = fields.Many2one(
        "ir.actions.client", string="Action", copy=False
    )
    menu_sequence = fields.Integer(string="Sequence", default=1, tracking=True)
    menu_active = fields.Boolean(string="Menu Active", default=True)
    grid_stack_dimensions = fields.Json(
        string="Grid Stack Dimensions", default=[], copy=False
    )
    auto_reload_duration = fields.Selection(
        [
            ("15000", "15 Seconds"),
            ("30000", "30 Seconds"),
            ("45000", "45 Seconds"),
            ("60000", "1 Minute"),
            ("120000", "2 Minutes"),
            ("300000", "5 Minutes"),
        ],
        default="120000",
        string="Auto-Refresh Interval",
        tracking=True,
    )
    mail_cron_id = fields.Many2one("ir.cron", string="Mail Cron Job", copy=False)
    dashboard_mail_ids = fields.One2many(
        "dashboard.mail",
        "dashboard_id",
        string="Dashboard Mail",
        help="Multiple different charts can be shared on mail to multiple different users.",
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        index=True,
        default=lambda self: self.env.company,
        help="Company related records.",
        tracking=True,
    )
    access_by = fields.Selection(
        [("access_group", "Access Groups"), ("user", "Users")],
        string="Access By",
        tracking=True,
    )
    group_ids = fields.Many2many(
        "res.groups",
        "dashboard_group_rel",
        "dashboard_id",
        "group_id",
        string="Access Groups",
    )
    user_ids = fields.Many2many(
        "res.users", "dashboard_user_rel", "dashboard_id", "user_id", string="Users"
    )

    def dashboard_export_json(self):
        charts_list = []
        for chart in self.chart_ids:
            chart_position = {}
            filtered_position = False
            if self.grid_stack_dimensions:
                filtered_position = list(
                    filter(
                        lambda grid: grid.get("chartId") == chart.id,
                        self.grid_stack_dimensions,
                    )
                )
            if filtered_position:
                chart_position = filtered_position[0]
            chart_dict = {
                "model": chart.model_id.model,
                "name": chart.name,
                "hide_false_value": chart.hide_false_value,
                "chart_type": chart.chart_type,
                "show_unit": chart.show_unit,
                "unit_type": chart.unit_type,
                "custom_unit": chart.custom_unit,
                "layout_type": chart.layout_type,
                "tile_layout_type": chart.tile_layout_type,
                "meter_target": chart.meter_target,
                "text_align": chart.text_align,
                "background_color": chart.background_color,
                "is_kpi_border": chart.is_kpi_border,
                "kpi_border_type": chart.kpi_border_type,
                "kpi_border_color": chart.kpi_border_color,
                "kpi_border_width": chart.kpi_border_width,
                "font_color": chart.font_color,
                "font_size": chart.font_size,
                "font_weight": chart.font_weight,
                "group_by_id": chart.group_by_id.name,
                "time_range": chart.time_range,
                "map_group_by_id": chart.map_group_by_id.name,
                "sub_group_by_id": chart.sub_group_by_id.name,
                "sub_time_range": chart.sub_time_range,
                "measurement_field_ids": chart.measurement_field_ids.mapped("name"),
                "sort_field_id": chart.sort_field_id.name,
                "sort_order": chart.sort_order,
                "limit_record": chart.limit_record,
                "date_filter_field_id": chart.date_filter_field_id.name,
                "date_filter_option": chart.date_filter_option,
                "domain": chart.evaluate_odoo_domain(chart.domain)
                if chart.domain
                else [],
                "data_type": chart.data_type,
                "measurement_field_id": chart.measurement_field_id.name,
                "include_periods": chart.include_periods,
                "same_period_previous_years": chart.same_period_previous_years,
                "list_type": chart.list_type,
                "icon_option": chart.icon_option,
                "default_icon": chart.default_icon,
                "icon": chart.icon,
                "kpi_model": chart.kpi_model_id.model,
                "kpi_data_type": chart.kpi_data_type,
                "kpi_measurement_field_id": chart.kpi_measurement_field_id.name,
                "kpi_limit_record": chart.kpi_limit_record,
                "kpi_domain": chart.evaluate_odoo_domain(chart.kpi_domain)
                if chart.kpi_domain
                else [],
                "kpi_date_filter_field_id": chart.kpi_date_filter_field_id.name,
                "kpi_date_filter_option": chart.kpi_date_filter_option,
                "kpi_include_periods": chart.kpi_include_periods,
                "kpi_same_period_previous_years": chart.kpi_same_period_previous_years,
                "kpi_comparison_type": chart.kpi_comparison_type,
                "kpi_enable_target": chart.kpi_enable_target,
                "kpi_target_value": chart.kpi_target_value,
                "kpi_view_type": chart.kpi_view_type,
                "previous_period_comparision": chart.previous_period_comparision,
                "previous_period_duration": chart.previous_period_duration,
                "previous_period_type": chart.previous_period_type,
                "is_apply_multiplier": chart.is_apply_multiplier,
                "todo_layout": chart.todo_layout,
                "todo_action_ids": [
                    {
                        "name": action.name,
                        "action_line_ids": [
                            {
                                "name": action_line.name,
                                "active_record": action_line.active_record,
                            }
                            for action_line in action.action_line_ids
                        ],
                    }
                    for action in chart.todo_action_ids
                ],
                "chart_multiplier_ids": [
                    {"field_id": m.field_id.name, "multiplier": m.multiplier}
                    for m in chart.chart_multiplier_ids
                ],
                "list_measure_ids": [
                    {
                        "sequence": m.sequence,
                        "list_field_id": m.list_field_id.name,
                        "list_measure_id": m.list_measure_id.name,
                        "value_type": m.value_type,
                        "model_id": m.model_id.model,
                        "field_id": m.field_id.name,
                    }
                    for m in chart.list_measure_ids
                ],
                "list_field_ids": [
                    {
                        "sequence": f.sequence,
                        "list_field_id": f.list_field_id.name,
                        "list_measure_id": f.list_measure_id.name,
                        "value_type": f.value_type,
                        "model_id": f.model_id.model,
                        "field_id": f.field_id.name,
                    }
                    for f in chart.list_field_ids
                ],
                "chart_position": chart_position,
            }
            charts_list.append(chart_dict)
        return charts_list

    def dashboard_import_json(self, json_payload):
        chart_vals_list = []
        unknown_model_list = []
        unknown_field_list = []
        dashboard_charts = self.env["dashboard.chart"]
        ir_model = self.env["ir.model"].sudo()
        ir_model_fields = self.env["ir.model.fields"].sudo()
        for payload in json_payload.get("json_payload"):
            model_id = ir_model.search([("model", "=", payload.get("model"))])
            if payload.get("model") and not model_id:
                unknown_model_list.append(payload.get("model"))
            group_by_id = ir_model_fields.search(
                [
                    ("model_id", "=", model_id.id),
                    ("name", "=", payload.get("group_by_id")),
                ]
            )
            if payload.get("group_by_id") and not group_by_id:
                unknown_field_list.append(payload.get("group_by_id"))
            map_group_by_id = ir_model_fields.search(
                [
                    ("model_id", "=", model_id.id),
                    ("name", "=", payload.get("map_group_by_id")),
                ]
            )
            if payload.get("map_group_by_id") and not map_group_by_id:
                unknown_field_list.append(payload.get("map_group_by_id"))
            sub_group_by_id = ir_model_fields.search(
                [
                    ("model_id", "=", model_id.id),
                    ("name", "=", payload.get("sub_group_by_id")),
                ]
            )
            if payload.get("sub_group_by_id") and not sub_group_by_id:
                unknown_field_list.append(payload.get("sub_group_by_id"))
            sort_field_id = ir_model_fields.search(
                [
                    ("model_id", "=", model_id.id),
                    ("name", "=", payload.get("sort_field_id")),
                ]
            )
            if payload.get("sort_field_id") and not sort_field_id:
                unknown_field_list.append(payload.get("sort_field_id"))
            measurement_field_id = ir_model_fields.search(
                [
                    ("model_id", "=", model_id.id),
                    ("name", "=", payload.get("measurement_field_id")),
                ]
            )
            if payload.get("measurement_field_id") and not measurement_field_id:
                unknown_field_list.append(payload.get("measurement_field_id"))
            date_filter_field_id = ir_model_fields.search(
                [
                    ("model_id", "=", model_id.id),
                    ("name", "=", payload.get("date_filter_field_id")),
                ]
            )
            if payload.get("date_filter_field_id") and not date_filter_field_id:
                unknown_field_list.append(payload.get("date_filter_field_id"))
            measurement_field_ids = ir_model_fields.search(
                [
                    ("model_id", "=", model_id.id),
                    ("name", "in", payload.get("measurement_field_ids")),
                ]
            )
            if payload.get("measurement_field_ids") and len(
                measurement_field_ids
            ) != len(payload.get("measurement_field_ids")):
                unknown_field_list.extend(payload.get("measurement_field_ids"))

            kpi_model_id = ir_model.search([("model", "=", payload.get("kpi_model"))])
            if payload.get("kpi_model") and not kpi_model_id:
                unknown_model_list.append(payload.get("kpi_model"))
            kpi_measurement_field_id = ir_model_fields.search(
                [
                    ("model_id", "=", kpi_model_id.id),
                    ("name", "=", payload.get("kpi_measurement_field_id")),
                ]
            )
            if payload.get("kpi_measurement_field_id") and not kpi_measurement_field_id:
                unknown_field_list.append(payload.get("kpi_measurement_field_id"))
            kpi_date_filter_field_id = ir_model_fields.search(
                [
                    ("model_id", "=", kpi_model_id.id),
                    ("name", "=", payload.get("kpi_date_filter_field_id")),
                ]
            )
            if payload.get("kpi_date_filter_field_id") and not kpi_date_filter_field_id:
                unknown_field_list.append(payload.get("kpi_date_filter_field_id"))
            chart_dict = {
                "model_id": model_id.id,
                "dashboard_id": self.id,
                "name": payload.get("name"),
                "hide_false_value": payload.get("hide_false_value"),
                "chart_type": payload.get("chart_type"),
                "show_unit": payload.get("show_unit"),
                "unit_type": payload.get("unit_type"),
                "custom_unit": payload.get("custom_unit"),
                "layout_type": payload.get("layout_type"),
                "tile_layout_type": payload.get("tile_layout_type"),
                "meter_target": payload.get("meter_target"),
                "text_align": payload.get("text_align"),
                "background_color": payload.get("background_color"),
                "is_kpi_border": payload.get("is_kpi_border"),
                "kpi_border_type": payload.get("kpi_border_type"),
                "kpi_border_color": payload.get("kpi_border_color"),
                "kpi_border_width": payload.get("kpi_border_width"),
                "font_color": payload.get("font_color"),
                "font_size": payload.get("font_size"),
                "font_weight": payload.get("font_weight"),
                "group_by_id": group_by_id.id,
                "time_range": payload.get("time_range"),
                "map_group_by_id": map_group_by_id.id,
                "sub_group_by_id": sub_group_by_id.id,
                "sub_time_range": payload.get("sub_time_range"),
                "measurement_field_ids": [(6, 0, measurement_field_ids.ids)],
                "sort_field_id": sort_field_id.id,
                "sort_order": payload.get("sort_order"),
                "limit_record": payload.get("limit_record"),
                "date_filter_field_id": date_filter_field_id.id,
                "date_filter_option": payload.get("date_filter_option"),
                "domain": payload.get("domain"),
                "data_type": payload.get("data_type"),
                "measurement_field_id": measurement_field_id.id,
                "include_periods": payload.get("include_periods"),
                "same_period_previous_years": payload.get("same_period_previous_years"),
                "list_type": payload.get("list_type"),
                "icon_option": payload.get("icon_option"),
                "default_icon": payload.get("default_icon"),
                "icon": payload.get("icon"),
                "kpi_model_id": kpi_model_id.id,
                "kpi_data_type": payload.get("kpi_data_type"),
                "kpi_measurement_field_id": kpi_measurement_field_id.id,
                "kpi_limit_record": payload.get("kpi_limit_record"),
                "kpi_domain": payload.get("kpi_domain"),
                "kpi_date_filter_field_id": kpi_date_filter_field_id.id,
                "kpi_date_filter_option": payload.get("kpi_date_filter_option"),
                "kpi_include_periods": payload.get("kpi_include_periods"),
                "kpi_same_period_previous_years": payload.get(
                    "kpi_same_period_previous_years"
                ),
                "kpi_comparison_type": payload.get("kpi_comparison_type"),
                "kpi_enable_target": payload.get("kpi_enable_target"),
                "kpi_target_value": payload.get("kpi_target_value"),
                "kpi_view_type": payload.get("kpi_view_type"),
                "previous_period_comparision": payload.get(
                    "previous_period_comparision"
                ),
                "previous_period_duration": payload.get("previous_period_duration"),
                "previous_period_type": payload.get("previous_period_type"),
                "is_apply_multiplier": payload.get("is_apply_multiplier"),
                "todo_layout": payload.get("todo_layout"),
                "todo_action_ids": [
                    {
                        "name": action.get("name"),
                        "action_line_ids": [
                            {
                                "name": action_line.get("name"),
                                "active_record": action_line.get("active_record"),
                            }
                            for action_line in action.get("action_line_ids")
                        ],
                    }
                    for action in payload.get("todo_action_ids")
                ],
            }
            multiplier_list = []
            list_measure_ids_list = []
            list_fields_ids_list = []
            for chart_multiplier in payload.get("chart_multiplier_ids"):
                multiplier_field = ir_model_fields.search(
                    [
                        ("model_id", "=", model_id.id),
                        ("name", "=", chart_multiplier.get("field_id")),
                    ]
                )
                if chart_multiplier.get("field_id") and not multiplier_field:
                    unknown_field_list.append(chart_multiplier.get("field_id"))
                multiplier_list.append(
                    (
                        0,
                        0,
                        {
                            "field_id": multiplier_field.id,
                            "multiplier": chart_multiplier.get("multiplier"),
                        },
                    )
                )
            chart_dict["chart_multiplier_ids"] = multiplier_list
            for chart_list_measure in payload.get("list_measure_ids"):
                list_field_id = ir_model_fields.search(
                    [
                        ("model_id", "=", model_id.id),
                        ("name", "=", chart_list_measure.get("list_field_id")),
                    ]
                )
                list_measure_id = ir_model_fields.search(
                    [
                        ("model_id", "=", model_id.id),
                        ("name", "=", chart_list_measure.get("list_measure_id")),
                    ]
                )
                if chart_list_measure.get("list_field_id") and not list_field_id:
                    unknown_field_list.append(chart_list_measure.get("list_field_id"))
                if chart_list_measure.get("list_measure_id") and not list_measure_id:
                    unknown_field_list.append(chart_list_measure.get("list_measure_id"))
                list_measure_ids_list.append(
                    (
                        0,
                        0,
                        {
                            "sequence": chart_list_measure.get("sequence"),
                            "list_field_id": list_field_id.id,
                            "list_measure_id": list_measure_id.id,
                            "value_type": chart_list_measure.get("value_type"),
                        },
                    )
                )
            chart_dict["list_measure_ids"] = list_measure_ids_list
            for chart_list_field in payload.get("list_field_ids"):
                list_field_id = ir_model_fields.search(
                    [
                        ("model_id", "=", model_id.id),
                        ("name", "=", chart_list_field.get("list_field_id")),
                    ]
                )
                list_measure_id = ir_model_fields.search(
                    [
                        ("model_id", "=", model_id.id),
                        ("name", "=", chart_list_field.get("list_measure_id")),
                    ]
                )
                if chart_list_field.get("list_field_id") and not list_field_id:
                    unknown_field_list.append(chart_list_field.get("list_field_id"))
                if chart_list_field.get("list_measure_id") and not list_measure_id:
                    unknown_field_list.append(chart_list_field.get("list_measure_id"))
                list_fields_ids_list.append(
                    (
                        0,
                        0,
                        {
                            "sequence": chart_list_field.get("sequence"),
                            "list_field_id": list_field_id.id,
                            "list_measure_id": list_measure_id.id,
                            "value_type": chart_list_field.get("value_type"),
                        },
                    )
                )
            chart_dict["list_field_ids"] = list_fields_ids_list
            chart_vals_list.append(chart_dict)
        if unknown_model_list or unknown_field_list:
            return {
                "type": "error",
                "message": "Unknown models: %s \n Unknown Fields: %s"
                % (
                    ", ".join(list(set(unknown_model_list))),
                    ", ".join(list(set(unknown_field_list))),
                ),
            }
        chart_records = dashboard_charts.create(chart_vals_list)
        grid_stack_dimensions = []
        for chart, payload in zip(chart_records, json_payload.get("json_payload")):
            position_payload = payload.get("chart_position")
            if position_payload:
                position_payload["chartId"] = chart.id
                grid_stack_dimensions.append(position_payload)
        self.write({"grid_stack_dimensions": grid_stack_dimensions})
        return {"type": "success"}

    def send_email(self, chartData):
        """
        Send dashboard charts emails to users
        """
        self.ensure_one()
        if self.created_menu_id:
            dashboard_emails = self.dashboard_mail_ids.filtered(
                lambda dmid: dmid.is_automated
            )
            if not dashboard_emails:
                return False
            for mail in dashboard_emails:
                items = []
                charts = mail.chart_ids
                for chart in charts:
                    chart_dict = {}
                    if chart.chart_type in ["kpi", "tile"]:
                        chart_dict = {
                            "chart_id": chart.id,
                            "name": chart.name,
                            "image": chart.html_to_image(),
                        }
                    else:
                        chart_data = chart.get_chart_data(chart.chart_type, chart.name)
                        chart_dict = {
                            "chart_id": chart.id,
                            "chart_type": chart.chart_type,
                            "name": chart.name,
                        }
                        if "default_icon" in chart_data and chart_data.get(
                            "default_icon"
                        ):
                            chart_data.update(
                                {"kpi_icon": Markup(chart_data.get("default_icon"))}
                            )
                        chart_dict.update(chart_data)
                    items.append(chart_dict)
                self.send_mail_to_users(mail, items)
            return True

    def send_mail_to_users(self, mail, items):
        """
        Send chart emails to users
        """
        emails = mail.recipient_ids.ids
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        url = "%s/web#db=%s&menu_id=%s&action_id=%s" % (
            base_url,
            self.env.cr.dbname,
            self.created_menu_id.id,
            self.created_action_id.id,
        )
        mail.mail_template_id.with_context(
            data=items,
            url=url,
            email_to=str(emails)[1:-1],
            name=self.name,
        ).send_mail(self.id, force_send=True)

    def scheduled_send_email(self, dashboard_id):
        """
        Send charts email to users
        """
        dashboard = self.browse(dashboard_id)
        composer = self.env["mail.compose.message"].sudo()
        ctx = {
            "default_model": "dashboard.dashboard",
            "default_res_ids": dashboard.ids,
            "default_composition_mode": "comment",
            "default_dashboard_id": dashboard.id,
            "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
            "email_notification_allow_footer": True,
            "emailData": {},
        }

        if len(self) > 1:
            ctx["default_composition_mode"] = "mass_mail"
        else:
            ctx.update(
                {
                    "force_email": True,
                    "model_description": "Dashboard Email",
                }
            )
        if dashboard:
            for mail in dashboard.dashboard_mail_ids.filtered(lambda m: m.is_automated):
                composer_id = composer.with_context(**ctx).create(
                    {"dashboard_id": dashboard.id}
                )
                composer_id.onchange_dashboard_id()
                composer_id.dashboard_mail_id = mail.id
                composer_id.onchange_dashboard_mail_id()
                composer_id.action_send_mail()

        return True

    @api.model_create_multi
    def create(self, vals):
        """
        Create cron job for dashboard
        """
        res = super(Dashboard, self).create(vals)
        for rec in res:
            cron_id = self.env["ir.cron"].create(
                {
                    "name": "Dashboard (%s): Send mail to the users" % (rec.name),
                    "model_id": self.env.ref(
                        "synconics_bi_dashboard.model_dashboard_dashboard"
                    ).id,
                    "state": "code",
                    "code": """model.scheduled_send_email(%s)""" % (rec.id),
                    "user_id": self.env.ref("base.user_root").id,
                    "interval_number": 1,
                    "interval_type": "days",
                }
            )
            rec.mail_cron_id = cron_id.id
        return res

    def unlink(self):
        """
        Delete dashboard menu
        """
        for rec in self:
            if rec.created_menu_id:
                raise ValidationError(
                    _(
                        "To delete selected dashboard, kindly click on Delete Menu first!"
                    )
                )
            # rec.action_delete_menu()
        return super(Dashboard, self).unlink()

    def action_view_charts(self):
        """
        To view dashboard charts
        """
        chart_ids = self.mapped("chart_ids")
        context = dict(self.env.context)
        action = self.env["ir.actions.actions"]._for_xml_id(
            "synconics_bi_dashboard.dashboard_chart_action"
        )
        if len(chart_ids) > 1:
            action["domain"] = [("id", "in", chart_ids.ids)]
        elif len(chart_ids) == 1:
            form_view = [
                (
                    self.env.ref("synconics_bi_dashboard.dashboard_chart_form_view").id,
                    "form",
                )
            ]
            action["views"] = form_view
            action["res_id"] = chart_ids.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        if action.get("context"):
            context.update(eval(action.get("context")))
        context.update(
            {
                "search_default_dashboard_id": self.id,
                "group_by": "dashboard_id",
                "default_dashboard_id": self.id,
            }
        )
        action["context"] = context
        return action

    def get_charts_details(self):
        """
        This function will return charts details and positioning and based on that
        charts will show in dashboard's menu
        """
        try:
            self.check_access("read")
        except Exception:
            return [1, []]
        chart_data_list = []
        grid_stack = self.grid_stack_dimensions or []
        existing_ids = {g["chartId"] for g in grid_stack}

        user = self.env.user
        is_dashboard_user = False
        if (
            user
            and user.has_group("synconics_bi_dashboard.group_dashboard_user")
            and not user.has_group("synconics_bi_dashboard.group_dashboard_manager")
        ):
            is_dashboard_user = True
        user_groups = user.group_ids.ids
        for chart in self.chart_ids:
            if (
                (chart.model_id and not user.has_read_access(chart.model_id))
                or (
                    chart.chart_type == "kpi"
                    and chart.kpi_model_id
                    and not user.has_read_access(chart.kpi_model_id)
                )
                or (
                    chart.group_ids
                    and not chart.group_ids.filtered(lambda g: g.id in user_groups)
                )
            ):
                continue

            if chart.id not in existing_ids:
                x, y = self.find_next_position(
                    grid_stack, 4 if chart.chart_type not in ["tile", "kpi"] else 2
                )
                new_dim = {
                    "chartId": chart.id,
                    "x": x,
                    "y": y,
                    "h": 4 if chart.chart_type not in ["tile", "kpi"] else 2,
                    "w": 6,
                }
                grid_stack.append(new_dim)
                dim = new_dim
            else:
                dim = next(g for g in grid_stack if g["chartId"] == chart.id)
            dim.update(
                {
                    "minh": 4
                    if chart.chart_type not in ["tile", "kpi", "to_do", "meter_chart"]
                    else 0
                }
            )
            chart_data_list.append(
                {
                    "id": str(chart.id),
                    "name": chart.name,
                    "chart_type": chart.chart_type,
                    "theme": chart.theme,
                    "recordset": chart.get_chart_data(chart.chart_type, chart.name),
                    "background_color": chart.background_color,
                    **{k: dim[k] for k in ("x", "y", "h", "w", "minh")},
                }
            )

        return [
            int(self.auto_reload_duration),
            chart_data_list,
            self.name,
            is_dashboard_user,
        ]

    def find_next_position(self, items, new_width, grid_columns=12):
        """
        In case of in any charts positioning is not saved then this function will evaluate positioning
        """
        if not items:
            return (0, 0)
        last_y = max((item["y"] for item in items if item["y"]), default=0)
        last_row = [item for item in items if item["y"] == last_y]

        used = sum(item["w"] for item in last_row)
        next_x = max((item["x"] + item["w"] for item in last_row), default=0)
        return (
            (next_x, last_y)
            if used + new_width <= grid_columns
            else (0, last_y + max(item["h"] or 2 for item in last_row))
        )

    def create_update_menu(self):
        """
        After creating dashboard, this function is responsible for creating/updating menu and actions
        """
        client_action = self.env["ir.actions.client"]
        ir_ui_menu = self.env["ir.ui.menu"]
        for rec in self:
            action_data = {
                "name": rec.name,
                "tag": "dashboard_amcharts",
                "params": {
                    "record": rec.id,
                    "menu_name": rec.name,
                    "dashboard_name": rec.name,
                },
            }
            vals = {}
            if not rec.created_action_id:
                action = client_action.create(
                    {
                        **action_data,
                        "binding_type": "action",
                        "target": "current",
                    }
                )
                vals["created_action_id"] = action.id
            else:
                action = rec.created_action_id
                rec.created_action_id.write(action_data)

            action_ref = f"ir.actions.client,{action.id}"
            menu_data = {
                "name": rec.name,
                "action": action_ref,
                "parent_id": rec.parent_menu_id.id,
                "sequence": rec.menu_sequence,
                "active": rec.menu_active,
            }
            if not rec.created_menu_id:
                menu = ir_ui_menu.create(menu_data)
                vals["created_menu_id"] = menu.id
            else:
                rec.created_menu_id.write(menu_data)
            rec.write(vals)
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def write(self, vals):
        for rec in self:
            if "menu_sequence" in vals and rec.created_menu_id:
                rec.created_menu_id.write({"sequence": vals["menu_sequence"]})
            if "name" in vals and rec.created_menu_id:
                rec.mail_cron_id.write(
                    {
                        "name": "Dashboard (%s): Send mail to the users"
                        % (vals["name"]),
                    }
                )
                rec.created_menu_id.write({"name": vals["name"]})
                rec.created_action_id.write({"name": vals["name"]})
            if "parent_menu_id" in vals and rec.created_menu_id:
                rec.created_menu_id.write({"parent_id": vals["parent_menu_id"]})
        return super(Dashboard, self).write(vals)

    def action_delete_menu(self):
        """
        Delete dashboard menu
        """
        for rec in self:
            if rec.menu_active and rec.created_menu_id:
                rec.created_menu_id.unlink()
            if rec.menu_active and rec.created_action_id:
                rec.created_action_id.unlink()
            if rec.mail_cron_id:
                rec.mail_cron_id.unlink()
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_dashboard_send(self, emailData=False):
        """
        Open popup to send mail to users about dashbaord layouts
        """
        dashboard_emails = self.dashboard_mail_ids
        if not dashboard_emails:
            return False
        ctx = {
            "default_model": "dashboard.dashboard",
            "default_res_ids": self.ids,
            "default_composition_mode": "comment",
            "default_dashboard_id": self.id,
            "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
            "email_notification_allow_footer": True,
            "emailData": emailData.get("emailData"),
            "is_dashboard": True,
        }

        if len(self) > 1:
            ctx["default_composition_mode"] = "mass_mail"
        else:
            ctx.update(
                {
                    "force_email": True,
                    "model_description": "Dashboard Email",
                }
            )
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }
        return action


class DashboardMail(models.Model):
    _name = "dashboard.mail"
    _description = "Dashboard Mail"

    def _default_mail_template(self):
        """
        Return default mail template
        """
        if self.env.ref("synconics_bi_dashboard.mail_template_dashboard_chart"):
            return self.env.ref(
                "synconics_bi_dashboard.mail_template_dashboard_chart"
            ).id

    dashboard_id = fields.Many2one("dashboard.dashboard", string="Dashboard")
    name = fields.Char(string="Name", required=True)
    mail_template_id = fields.Many2one(
        "mail.template",
        string="Mail Template",
        domain="[('model', '=', 'dashboard.dashboard')]",
        default=_default_mail_template,
        required=True,
    )
    chart_ids = fields.Many2many("dashboard.chart", string="Charts", required=True)
    recipient_ids = fields.Many2many("res.partner", string="Recipients", required=True)
    is_automated = fields.Boolean(string="Automated Email")

    @api.onchange("is_automated")
    def onchange_is_automated(self):
        if self.is_automated:
            self.chart_ids = [
                (3, chart.id)
                for chart in self.chart_ids.filtered(
                    lambda cid: cid.chart_type not in ["kpi", "tile", "list", "to_do"]
                )
            ]
