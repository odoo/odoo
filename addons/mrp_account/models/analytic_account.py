from odoo import _, api, fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    production_ids = fields.Many2many(comodel_name="mrp.production")
    production_count = fields.Count(
        count_of="production_ids",
        string="Manufacturing Orders Count",
    )
    bom_ids = fields.Many2many(comodel_name="mrp.bom")
    bom_count = fields.Count(
        count_of="bom_ids",
        string="BoM Count",
    )
    workcenter_ids = fields.Many2many(comodel_name="mrp.workcenter")
    workorder_count = fields.Integer(
        string="Work Order Count",
        compute="_compute_workorder_count",
    )

    def _get_workorders(self):
        return self.workcenter_ids.order_ids | self.production_ids.workorder_ids

    @api.depends("workcenter_ids.order_ids", "production_ids.workorder_ids")
    def _compute_workorder_count(self):
        for account in self:
            account.workorder_count = len(account._get_workorders())

    def _action_view_linked(self, records, name, **action):
        self.check_singleton()
        action = {
            "type": "ir.actions.act_window",
            "res_model": records._name,
            "domain": [("id", "in", records.ids)],
            "name": name,
            "view_mode": "list,form",
            **action,
        }
        if len(records) == 1:
            action["view_mode"] = "form"
            action["res_id"] = records.id
        return action

    def action_view_mrp_production(self):
        return self._action_view_linked(
            self.production_ids,
            _("Manufacturing Orders"),
            context={"default_analytic_account_id": self.id},
        )

    def action_view_mrp_bom(self):
        return self._action_view_linked(
            self.bom_ids,
            _("Bills of Materials"),
            context={"default_analytic_account_id": self.id},
        )

    def action_view_workorder(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mrp.workorder",
            "domain": [("id", "in", self._get_workorders().ids)],
            "context": {"create": False},
            "name": _("Work Orders"),
            "view_mode": "list",
        }


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    category = fields.Selection(
        selection_add=[("manufacturing_order", "Manufacturing Order")]
    )


class AccountAnalyticApplicability(models.Model):
    _inherit = "account.analytic.applicability"

    business_domain = fields.Selection(
        selection_add=[
            ("manufacturing_order", "Manufacturing Order"),
        ],
        ondelete={"manufacturing_order": "cascade"},
    )
