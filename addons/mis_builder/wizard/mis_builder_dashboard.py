# Copyright 2014 ACSONE SA/NV (<http://acsone.eu>)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo import api, fields, models


class AddMisReportInstanceDashboard(models.TransientModel):
    _name = "add.mis.report.instance.dashboard.wizard"
    _description = "MIS Report Add to Dashboard Wizard"

    name = fields.Char(required=True)

    dashboard_id = fields.Many2one(
        "ir.actions.act_window",
        string="Dashboard",
        required=True,
        domain="[('res_model', '=', " "'board.board')]",
    )

    @api.model
    def default_get(self, fields_list):
        res = {}
        if self.env.context.get("active_id", False):
            res = super().default_get(fields_list)
            # get report instance name
            res["name"] = (
                self.env["mis.report.instance"]
                .browse(self.env.context["active_id"])
                .name
            )
        return res

    def action_add_to_dashboard(self):
        active_model = self.env.context.get("active_model")
        assert active_model == "mis.report.instance"
        active_id = self.env.context.get("active_id")
        assert active_id
        # create the act_window corresponding to this report
        self.env.ref("mis_builder.mis_report_instance_result_view_form")
        view = self.env.ref("mis_builder.mis_report_instance_result_view_form")
        report_result = (
            self.env["ir.actions.act_window"]
            .sudo()
            .create(
                {
                    "name": "mis.report.instance.result.view.action.%d"
                    % self.env.context["active_id"],
                    "res_model": active_model,
                    "res_id": active_id,
                    "target": "current",
                    "view_mode": "form",
                    "view_id": view.id,
                    "context": self.env.context,
                }
            )
        )
        # add this result in the selected dashboard
        last_customization = self.env["ir.ui.view.custom"].search(
            [
                ("user_id", "=", self.env.uid),
                ("ref_id", "=", self.dashboard_id.view_id.id),
            ],
            limit=1,
        )
        arch = self.dashboard_id.view_id.arch
        if last_customization:
            arch = self.env["ir.ui.view.custom"].browse(last_customization[0].id).arch
        new_arch = etree.fromstring(arch)
        column = new_arch.xpath("//column")[0]
        # Due to native dashboard doesn't support form view
        # add "from_dashboard" to context to get correct views in "get_views"
        context = dict(self.env.context, from_dashboard=True)
        column.append(
            etree.Element(
                "action",
                {
                    "context": str(context),
                    "name": str(report_result.id),
                    "string": self.name,
                    "view_mode": "form",
                },
            )
        )
        self.env["ir.ui.view.custom"].create(
            {
                "user_id": self.env.uid,
                "ref_id": self.dashboard_id.view_id.id,
                "arch": etree.tostring(new_arch, pretty_print=True),
            }
        )

        return {"type": "ir.actions.act_window_close"}
