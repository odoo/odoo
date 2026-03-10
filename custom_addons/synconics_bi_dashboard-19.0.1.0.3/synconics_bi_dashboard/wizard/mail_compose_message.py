from odoo import models, fields, api
from markupsafe import Markup


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.model
    def default_get(self, fields):
        """
        Set default dashboard value on mail compose wizard
        """
        res = super(MailComposeMessage, self).default_get(fields)
        context = dict(self.env.context)
        if context.get("active_model") == "dashboard.dashboard" and context.get(
            "active_id"
        ):
            res.update({"dashboard_id": context["active_id"]})
        return res

    dashboard_id = fields.Many2one("dashboard.dashboard", string="Dashboard")
    dashboard_mail_id = fields.Many2one("dashboard.mail", string="Dashboard Mail")
    chart_ids = fields.Many2many("dashboard.chart", string="Charts")

    @api.onchange("dashboard_id")
    def onchange_dashboard_id(self):
        """
        Set charts base on dashboard
        """
        if self.dashboard_id:
            self.dashboard_mail_id = False
            self.chart_ids = False

    @api.onchange("dashboard_mail_id")
    def onchange_dashboard_mail_id(self):
        """
        To set charts and parters to send dashboard mail
        """
        context = dict(self.env.context)
        if not context.get("is_dashboard", False):
            return
        self.chart_ids = False
        self.template_id = False
        if self.dashboard_mail_id:
            self.chart_ids = [
                (
                    6,
                    0,
                    self.dashboard_mail_id.chart_ids.filtered(
                        lambda cid: not (
                            cid.chart_type == "to_do" and cid.todo_layout == "default"
                        )
                    ).ids,
                )
            ]
            self.partner_ids = [(6, 0, self.dashboard_mail_id.recipient_ids.ids)]
            self.template_id = self.dashboard_mail_id.mail_template_id.id
        items = []
        charts = self.chart_ids.filtered(
            lambda cid: not (cid.chart_type == "to_do" and cid.todo_layout == "default")
        )
        chart_id_list = []
        for key, value in context.get("emailData", {}).items():
            if int(key) in charts.ids:
                chart_id_list.append(int(key))
                chart_dict = {"chart_id": key}
                chart_dict.update(value)
                items.append(chart_dict)
        charts = charts._origin.filtered(
            lambda cid: cid._origin.id not in chart_id_list
        )
        for chart in charts:
            chart_dict = {}
            if chart.chart_type == "to_do" and chart.todo_layout != "activity":
                continue
            if chart.chart_type in ["kpi", "tile", "to_do", "list"]:
                image = chart.html_to_image()
                chart_dict = {"chart_id": chart.id, "name": chart.name, "image": image}
            else:
                chart_data = chart.get_chart_data(chart.chart_type, chart.name)
                chart_dict = {
                    "chart_id": chart.id,
                    "chart_type": chart.chart_type,
                    "name": chart.name,
                }
                if "default_icon" in chart_data and chart_data.get("default_icon"):
                    chart_data.update(
                        {"kpi_icon": Markup(chart_data.get("default_icon"))}
                    )
                chart_dict.update(chart_data)
            items.append(chart_dict)
        context.update({"data": items})
        self.env = self.env(context=context)

    @api.onchange("chart_ids")
    def onchange_chart_ids(self):
        context = dict(self.env.context)
        if not context.get("is_dashboard", False):
            return
        self.template_id = self.dashboard_mail_id.mail_template_id.id
        items = []
        charts = self.chart_ids
        chart_id_list = []
        for key, value in context.get("emailData", {}).items():
            if int(key) in charts.ids:
                chart_id_list.append(int(key))
                chart_dict = {"chart_id": key}
                chart_dict.update(value)
                items.append(chart_dict)
        charts = charts.filtered(lambda cid: cid._origin.id not in chart_id_list)
        for chart in charts:
            chart_dict = {}
            if chart.chart_type == "to_do" and chart.todo_layout != "activity":
                continue
            if chart.chart_type in ["kpi", "tile", "to_do", "list"]:
                image = chart.html_to_image()
                chart_dict = {"chart_id": chart.id, "name": chart.name, "image": image}
            else:
                chart_data = chart.get_chart_data(chart.chart_type, chart.name)
                chart_dict = {
                    "chart_id": chart.id,
                    "chart_type": chart.chart_type,
                    "name": chart.name,
                }
                if "default_icon" in chart_data and chart_data.get("default_icon"):
                    chart_data.update(
                        {"kpi_icon": Markup(chart_data.get("default_icon"))}
                    )
                chart_dict.update(chart_data)
            items.append(chart_dict)
        context.update({"data": items})
        self.env = self.env(context=context)
