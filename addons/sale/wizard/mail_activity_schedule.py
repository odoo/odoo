# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    sale_order_id = fields.Many2one(
        "sale.order",
        compute="_compute_sale_order_id",
        store=False,
        readonly=False,
    )
    sale_order_id_domain = fields.Char(
        compute="_compute_sale_order_id_domain",
        export_string_translation=False,
    )

    @api.depends_context("log_contact_id")
    def _compute_sale_order_id_domain(self):
        if contact := self.env["res.partner"].browse(self.env.context.get("log_contact_id")):
            all_child = self.env["res.partner"].with_context(active_test=False).search([("id", "child_of", contact.id)])
            sale_order_id_domain = [("partner_id", "in", (contact | all_child).ids)]
        else:
            sale_order_id_domain = []
        self.sale_order_id_domain = sale_order_id_domain

    def _get_res_model_fields(self):
        return {**super()._get_res_model_fields(), "sale.order": "sale_order_id"}

    def _selection_res_model(self):
        res = super()._selection_res_model()
        if self.env.user.has_group("sales_team.group_sale_salesman"):
            res += [("sale.order", self.env._("Sale Order"))]
        return res

    @api.depends("res_model_selection", "sale_order_id_domain")
    def _compute_sale_order_id(self):
        for activity in self:
            if activity.sale_order_id or activity.res_model_selection != "sale.order":
                continue
            domain = literal_eval(activity.sale_order_id_domain)
            activity.sale_order_id = self.env.context.get("default_sale_order_id") or activity.env["sale.order"].search(
                domain, limit=1, order="id desc",
            )
