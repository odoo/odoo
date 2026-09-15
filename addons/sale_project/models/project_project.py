import json
from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query
from odoo.tools.misc import unquote
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = "project.project"

    def _domain_sale_line_id(self):
        return Domain.AND(
            [
                self.env["sale.order.line"]._get_domain_lines_sellable(),
                self.env["sale.order.line"]._domain_sale_line_service(),
                [
                    ("partner_id", "=?", unquote("partner_id")),
                ],
            ]
        )

    allow_billable = fields.Boolean(string="Billable")
    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sales Order Item",
        compute="_compute_sale_line_id",
        store=True,
        index="btree_not_null",
        copy=False,
        readonly=False,
        domain=lambda self: str(self._domain_sale_line_id()),
        help="Sales order item that will be selected by default on the tasks and timesheets of this project,"
        " except if the employee set on the timesheets is explicitely linked to another sales order item on the project.\n"
        "It can be modified on each task and timesheet entry individually if necessary.",
    )
    sale_order_id = fields.Many2one(
        related="sale_line_id.order_id",
        export_string_translation=False,
    )
    has_any_so_to_invoice = fields.Boolean(
        string="Has SO to Invoice",
        export_string_translation=False,
        compute="_compute_has_any_so_to_invoice",
    )
    sale_order_line_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_sale_order_count",
        groups="sale.group_sale_salesman",
    )
    sale_order_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_sale_order_count",
        groups="sale.group_sale_salesman",
    )
    has_any_so_with_nothing_to_invoice = fields.Boolean(
        string="Has a SO with an invoice status of No",
        export_string_translation=False,
        compute="_compute_has_any_so_with_nothing_to_invoice",
    )
    invoice_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_invoice_count",
        groups="account.group_account_readonly",
    )
    vendor_bill_count = fields.Integer(
        related="account_id.vendor_bill_count",
        export_string_translation=False,
        compute_sudo=False,
        groups="account.group_account_readonly",
    )
    partner_id = fields.Many2one(
        compute="_compute_partner_id",
        store=True,
        readonly=False,
    )
    display_sales_stat_buttons = fields.Boolean(
        export_string_translation=False,
        compute="_compute_display_sales_stat_buttons",
    )
    sale_order_state = fields.Selection(
        related="sale_order_id.state",
        export_string_translation=False,
    )
    reinvoiced_sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        index="btree_not_null",
        copy=False,
        domain="[('partner_id', '=', partner_id)]",
        groups="sale.group_sale_salesman",
        help="Products added to stock pickings, whose operation type is configured to generate analytic costs, will be re-invoiced in this sales order if they are set up for it.",
    )

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if self.env.context.get("order_state") == "done":
            order_id = self.env.context.get("order_id")
            sale_line_id = (
                self.env["sale.order.line"]
                .search(
                    [("order_id", "=", order_id), ("is_service", "=", True)], limit=1
                )
                .id
            )
            defaults.update(
                {
                    "reinvoiced_sale_order_id": order_id,
                    "sale_line_id": sale_line_id,
                }
            )
        return defaults

    @api.model
    def _prepare_map_tasks_defaults(self, project):
        defaults = super()._prepare_map_tasks_defaults(project)
        defaults["sale_line_id"] = False
        return defaults

    @api.depends("partner_id")
    def _compute_sale_line_id(self):
        if _debug.logic.enabled:
            _debug.logic(
                "sale_line_cleared_on_partner_mismatch",
                projects=self.filtered(
                    lambda p: (
                        p.sale_line_id
                        and (
                            not p.partner_id
                            or p.sale_line_id.partner_id.commercial_partner_id
                            != p.partner_id.commercial_partner_id
                        )
                    )
                ),
            )
        self.filtered(
            lambda p: (
                p.sale_line_id
                and (
                    not p.partner_id
                    or p.sale_line_id.partner_id.commercial_partner_id
                    != p.partner_id.commercial_partner_id
                )
            )
        ).update({"sale_line_id": False})

    def _get_projects_for_invoice_state(self, invoice_state):
        result = self.env.execute_query(
            SQL(
                """
            SELECT id
              FROM project_project pp
             WHERE pp.active = true
               AND (   EXISTS(SELECT 1
                                FROM sale_order so
                                JOIN project_task pt ON pt.sale_order_id = so.id
                               WHERE pt.project_id = pp.id
                                 AND pt.active = true
                                 AND so.invoice_state = %(invoice_state)s)
                    OR EXISTS(SELECT 1
                                FROM sale_order so
                                JOIN sale_order_line sol ON sol.order_id = so.id
                               WHERE sol.id = pp.sale_line_id
                                 AND so.invoice_state = %(invoice_state)s))
               AND id in %(ids)s""",
                ids=tuple(self.ids),
                invoice_state=invoice_state,
            )
        )
        _debug.perf.count(
            "projects_for_invoice_state",
            projects=len(self),
            state=invoice_state,
            matched=len(result),
        )
        return self.env["project.project"].browse(id_ for (id_,) in result)

    @api.depends("sale_order_id.invoice_state", "task_ids.sale_order_id.invoice_state")
    def _compute_has_any_so_to_invoice(self):
        if not self.ids:
            self.has_any_so_to_invoice = False
            return

        project_to_invoice = self._get_projects_for_invoice_state("to do")
        project_to_invoice |= self._get_projects_for_invoice_state("partial")
        project_to_invoice.has_any_so_to_invoice = True
        (self - project_to_invoice).has_any_so_to_invoice = False

    @api.depends("sale_order_id", "task_ids.sale_order_id")
    def _compute_sale_order_count(self):
        sale_order_items_per_project_id = self._get_sale_order_items_per_project_id(
            {"project.task": [("is_closed", "=", False)]}
        )
        for project in self:
            sale_order_lines = sale_order_items_per_project_id.get(
                project.id, self.env["sale.order.line"]
            )
            project.sale_order_line_count = len(sale_order_lines)

            project.sale_order_count = len(
                sale_order_lines.sudo().order_id or project.reinvoiced_sale_order_id
            )
            _debug.logic(
                "project_sale_counts",
                project=project,
                lines=project.sale_order_line_count,
                orders=project.sale_order_count,
            )

    @api.depends("account_id")
    def _compute_invoice_count(self):
        data = self.env["account.move.line"]._read_group(
            [
                ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                ("analytic_distribution", "in", self.account_id.ids),
            ],
            groupby=["analytic_distribution"],
            aggregates=["__count"],
        )
        data = {int(account_id): move_count for account_id, move_count in data}
        _debug.perf.count(
            "project_invoice_count", projects=len(self), accounts=len(data)
        )
        for project in self:
            project.invoice_count = data.get(project.account_id.id, 0)

    @api.depends("allow_billable", "partner_id")
    def _compute_display_sales_stat_buttons(self):
        for project in self:
            project.display_sales_stat_buttons = (
                project.allow_billable and project.partner_id
            )

    def action_customer_preview(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": self.get_portal_url(),
        }

    @api.onchange("reinvoiced_sale_order_id")
    def _onchange_reinvoiced_sale_order_id(self):
        if not self.sale_line_id and (
            service_sols := self.reinvoiced_sale_order_id.line_ids.filtered(
                "is_service"
            )
        ):
            _debug.logic(
                "sale_line_from_reinvoiced_order",
                project=self._origin,
                line=service_sols[0],
            )
            self.sale_line_id = service_sols[0]

    @api.onchange("sale_line_id")
    def _onchange_sale_line_id(self):
        reinvoiced = self._fields["reinvoiced_sale_order_id"]
        if (
            self.sale_line_id
            and self._has_field_access(reinvoiced, "write")
            and not self.reinvoiced_sale_order_id
        ):
            _debug.logic(
                "reinvoiced_order_from_sale_line",
                project=self._origin,
                order=self.sale_line_id.order_id,
            )
            self.reinvoiced_sale_order_id = self.sale_line_id.order_id

    def _confirm_linked_sale_orders(self, sol_ids):
        quotations = (
            self.env["sale.order.line"]
            .sudo()
            ._read_group(
                domain=[("state", "=", "draft"), ("id", "in", sol_ids)],
                aggregates=["order_id:recordset"],
            )[0][0]
        )
        if quotations:
            _debug.pipeline(
                "linked_quotations_confirmed", projects=self, orders=quotations
            )
            quotations.action_confirm()

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        sol_ids = set()
        for project, vals in zip(projects, vals_list, strict=True):
            if vals.get("sale_line_id"):
                sol_ids.add(vals["sale_line_id"])
            if project.sale_order_id and not project.sale_order_id.project_id:
                project.sale_order_id.project_id = project.id
            elif (
                project.sudo().reinvoiced_sale_order_id
                and not project.sudo().reinvoiced_sale_order_id.project_id
            ):
                project.sudo().reinvoiced_sale_order_id.project_id = project.id
        _debug.lifecycle(
            "create", projects=projects, rows=len(vals_list), linked_lines=len(sol_ids)
        )
        if sol_ids:
            projects._confirm_linked_sale_orders(list(sol_ids))
        return projects

    def write(self, vals):
        project = super().write(vals)
        _debug.lifecycle("write", projects=self, fields=list(vals))
        if sol_id := vals.get("sale_line_id"):
            self._confirm_linked_sale_orders([sol_id])
        return project

    def _get_domain_sale_orders(self, all_sale_orders):
        return [("id", "in", all_sale_orders.ids)]

    def _get_view_action(self):
        return self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "sale.action_sale_order"
        )

    def action_view_sols(self):
        self.check_singleton()
        all_sale_order_lines = self._get_sale_order_items(
            {"project.task": [("is_closed", "=", False)]}
        )
        action_window = {
            "type": "ir.actions.act_window",
            "res_model": "sale.order.line",
            "name": _("%(name)s's Sales Order Items", name=self.name),
            "context": {
                "show_sale": True,
                "link_to_project": self.id,
                "form_view_ref": "sale_project.sale_order_line_view_form_editable",
                "action_view_sols": True,
                "default_partner_id": self.partner_id.id,
                "default_company_id": self.company_id.id,
                "default_order_id": self.sale_order_id.id,
            },
            "views": [
                (
                    self.env.ref("sale_project.sale_order_line_view_form_editable").id,
                    "form",
                )
            ],
        }
        if len(all_sale_order_lines) <= 1:
            action_window["res_id"] = all_sale_order_lines.id
        else:
            action_window.update(
                {
                    "domain": [("id", "in", all_sale_order_lines.ids)],
                    "views": [
                        (
                            self.env.ref(
                                "sale_project.view_sale_order_line_list_with_create"
                            ).id,
                            "list",
                        ),
                        (
                            self.env.ref(
                                "sale_project.sale_order_line_view_form_editable"
                            ).id,
                            "form",
                        ),
                    ],
                }
            )
        return action_window

    def action_view_sos(self):
        self.check_singleton()
        all_sale_orders = (
            self._get_sale_order_items({"project.task": [("is_closed", "=", False)]})
            .sudo()
            .order_id
        )
        embedded_action_context = self.env.context.get("from_embedded_action", False)
        action_window = self._get_view_action()
        action_window["display_name"] = self.env._(
            "%(name)s's %(action_name)s",
            name=self.name,
            action_name=action_window.get("name"),
        )
        action_window["domain"] = self._get_domain_sale_orders(all_sale_orders)
        action_window["context"] = {
            **self.env["ir.actions.actions"]._eval_action_context(
                action_window["context"]
            ),
            "create": self.env.context.get(
                "create_for_project_id", embedded_action_context
            ),
            "show_sale": True,
            "default_partner_id": self.partner_id.id,
            "default_project_id": self.id,
            "create_for_project_id": self.id if not embedded_action_context else False,
            "from_embedded_action": embedded_action_context,
        }
        if len(all_sale_orders) <= 1 and not embedded_action_context:
            action_window.update(
                {
                    "res_id": all_sale_orders.id,
                    "views": [[False, "form"]],
                }
            )
        return action_window

    def action_get_list_view(self):
        action = super().action_get_list_view()
        if self.allow_billable:
            action["views"] = [
                (self.env.ref("sale_project.project_milestone_view_tree").id, view_type)
                if view_type == "list"
                else (view_id, view_type)
                for view_id, view_type in action["views"]
            ]
        return action

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        if section_name in ["service_revenues", "materials"]:
            view_types = ["list", "kanban", "form"]
            action = {
                "name": _("Sales Order Items"),
                "type": "ir.actions.act_window",
                "res_model": "sale.order.line",
                "context": {"create": False, "edit": False},
            }
            if res_id:
                action["res_id"] = res_id
                view_types = ["form"]
            else:
                action["domain"] = domain
            action["views"] = [(False, v) for v in view_types]
            return action

        if section_name in ["other_invoice_revenues", "downpayments"]:
            action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "account.action_move_out_invoice_type"
            )
            action["domain"] = domain or []
            action["context"] = {
                **self.env["ir.actions.actions"]._eval_action_context(
                    action["context"]
                ),
                "default_partner_id": self.partner_id.id,
                "project_id": self.id,
            }
            if res_id:
                action["views"] = [(False, "form")]
                action["view_mode"] = "form"
                action["res_id"] = res_id
            return action

        if section_name == "cost_of_goods_sold":
            return {
                "name": _("Cost of Goods Sold Items"),
                "type": "ir.actions.act_window",
                "res_model": "account.move.line",
                "views": [[False, "list"], [False, "form"]],
                "domain": [("move_id", "=", res_id), ("display_type", "=", "cogs")],
                "context": {"create": False, "edit": False},
            }

        return super().action_profitability_items(section_name, domain, res_id)

    @api.depends("sale_order_id.invoice_state", "task_ids.sale_order_id.invoice_state")
    def _compute_has_any_so_with_nothing_to_invoice(self):
        if not self.ids:
            self.has_any_so_with_nothing_to_invoice = False
            return

        project_nothing_to_invoice = self._get_projects_for_invoice_state("no")
        project_nothing_to_invoice.has_any_so_with_nothing_to_invoice = True
        (self - project_nothing_to_invoice).has_any_so_with_nothing_to_invoice = False

    def action_create_invoice(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "sale.action_view_sale_advance_payment_inv"
        )
        so_ids = (
            (self.sale_order_id | self.task_ids.sale_order_id)
            .filtered(lambda so: so.invoice_state in ["to do", "partial", "no"])
            .ids
        )
        action["context"] = {
            "active_id": so_ids[0] if len(so_ids) == 1 else False,
            "active_ids": so_ids,
        }
        _debug.logic("project_invoice_action", project=self, orders=len(so_ids))
        if not self.has_any_so_to_invoice:
            action["context"]["default_advance_payment_method"] = "percentage"
        return action

    def action_view_project_invoices(self):
        move_lines = self.env["account.move.line"].search_fetch(
            [
                ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                ("analytic_distribution", "in", self.account_id.ids),
            ],
            ["move_id"],
        )
        invoice_ids = move_lines.move_id.ids
        action = {
            "name": _("Invoices"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "views": [[False, "list"], [False, "form"], [False, "kanban"]],
            "domain": [("id", "in", invoice_ids)],
            "context": {
                "default_move_type": "out_invoice",
                "default_partner_id": self.partner_id.id,
                "project_id": self.id,
            },
            "help": "<p class='o_view_nocontent_smiling_face'>%s</p><p>%s</p>"
            % (
                _("Create a customer invoice"),
                _(
                    "Create invoices, register payments and keep track of the discussions with your customers."
                ),
            ),
        }
        if len(invoice_ids) == 1 and not self.env.context.get(
            "from_embedded_action", False
        ):
            action["views"] = [[False, "form"]]
            action["res_id"] = invoice_ids[0]
        return action

    def _get_sale_order_items_per_project_id(self, domain_per_model=None):
        if not self:
            return {}
        if len(self) == 1:
            return {self.id: self._get_sale_order_items(domain_per_model)}
        sql = self._get_sale_order_items_query(domain_per_model).select(
            "id", "ARRAY_AGG(DISTINCT sale_line_id) AS sale_line_ids"
        )
        sql = SQL("%s GROUP BY id", sql)
        return {
            id_: self.env["sale.order.line"].browse(sale_line_ids)
            for id_, sale_line_ids in self.env.execute_query(sql)
        }

    def _get_sale_order_items(self, domain_per_model=None, limit=None, offset=None):
        return self.env["sale.order.line"].browse(
            self._get_sale_order_item_ids(domain_per_model, limit, offset)
        )

    def _get_sale_order_item_ids(self, domain_per_model=None, limit=None, offset=None):
        if not self or not self.filtered("allow_billable"):
            _debug.logic("sale_items_skipped", projects=self, reason="not_billable")
            return []
        query = self._get_sale_order_items_query(domain_per_model)
        query.limit = limit
        query.offset = offset
        return [
            id_
            for (id_,) in self.env.execute_query(query.select("DISTINCT sale_line_id"))
        ]

    def _get_sale_orders(self):
        return self._get_sale_order_items().order_id

    def _get_sale_order_items_query(self, domain_per_model=None):
        if domain_per_model is None:
            domain_per_model = {}
        billable_project_domain = [("allow_billable", "=", True)]
        project_domain = [("id", "in", self.ids), ("sale_line_id", "!=", False)]
        if "project.project" in domain_per_model:
            project_domain = Domain.AND(
                [
                    domain_per_model["project.project"],
                    project_domain,
                    billable_project_domain,
                ]
            )
        project_query = self.env["project.project"]._search(project_domain)
        project_sql = project_query.select(
            f"{self._table}.id ", f"{self._table}.sale_line_id"
        )

        Task = self.env["project.task"]
        task_domain = [("project_id", "in", self.ids), ("sale_line_id", "!=", False)]
        if Task._name in domain_per_model:
            task_domain = Domain.AND(
                [
                    domain_per_model[Task._name],
                    task_domain,
                ]
            )
        task_query = Task._search(task_domain)
        task_sql = task_query.select(
            f"{Task._table}.project_id AS id", f"{Task._table}.sale_line_id"
        )

        ProjectMilestone = self.env["project.milestone"]
        milestone_domain = [
            ("project_id", "in", self.ids),
            ("allow_billable", "=", True),
            ("sale_line_id", "!=", False),
        ]
        if ProjectMilestone._name in domain_per_model:
            milestone_domain = Domain.AND(
                [
                    domain_per_model[ProjectMilestone._name],
                    milestone_domain,
                    billable_project_domain,
                ]
            )
        milestone_query = ProjectMilestone._search(milestone_domain)
        milestone_sql = milestone_query.select(
            f"{ProjectMilestone._table}.project_id AS id",
            f"{ProjectMilestone._table}.sale_line_id",
        )

        SaleOrderLine = self.env["sale.order.line"]
        sale_order_line_domain = [
            "&",
            ("display_type", "=", False),
            (
                "order_id",
                "any",
                [
                    "|",
                    ("id", "in", self.reinvoiced_sale_order_id.ids),
                    ("project_id", "in", self.ids),
                ],
            ),
        ]
        sale_order_line_query = SaleOrderLine._search(
            sale_order_line_domain, bypass_access=True
        )
        sale_order_line_sql = sale_order_line_query.select(
            f"{SaleOrderLine._table}.project_id AS id",
            f"{SaleOrderLine._table}.id AS sale_line_id",
        )

        return Query(
            self.env,
            "project_sale_order_item",
            SQL(
                "(%s)",
                SQL(" UNION ").join(
                    [
                        project_sql,
                        task_sql,
                        milestone_sql,
                        sale_order_line_sql,
                    ]
                ),
            ),
        )

    def get_panel_data(self):
        panel_data = super().get_panel_data()
        foldable_sections = self._get_foldable_section()
        if (
            self._is_profitability_shown()
            and "revenues" in panel_data["profitability_items"]
        ):
            for section in panel_data["profitability_items"]["revenues"]["data"]:
                if section["id"] in foldable_sections:
                    section["isSectionFoldable"] = True
        return {
            **panel_data,
            "show_sale_items": self.allow_billable,
        }

    def _get_foldable_section(self):
        return ["materials", "service_revenues"]

    def get_sale_items_data(
        self, offset=0, limit=None, with_action=True, section_id=None
    ):
        if not self.env.user.has_group("project.group_project_user"):
            return {}

        all_sols = (
            self.env["sale.order.line"]
            .sudo()
            .search(
                self._get_domain_from_section_id(section_id),
                offset=offset,
                limit=limit + 1,
            )
        )
        display_load_more = False
        if len(all_sols) > limit:
            all_sols -= all_sols[limit]
            display_load_more = True

        action_per_sol = (
            all_sols.sudo(False)._filtered_access("read")._get_action_per_item()
            if with_action
            else {}
        )

        def get_action(sol_id):
            action, res_id = action_per_sol.get(sol_id, (None, None))
            return (
                {
                    "action": {
                        "name": action,
                        "resId": res_id,
                        "buttonContext": json.dumps(
                            {"active_id": sol_id, "default_project_id": self.id}
                        ),
                    }
                }
                if action
                else {}
            )

        return {
            "sol_items": [
                {
                    **sol_read,
                    **get_action(sol_read["id"]),
                }
                for sol_read in all_sols.with_context(
                    with_price_unit=True
                )._read_format(
                    [
                        "display_name",
                        "product_qty",
                        "qty_transferred",
                        "qty_invoiced",
                        "product_uom_id",
                        "product_id",
                    ]
                )
            ],
            "displayLoadMore": display_load_more,
        }

    def _get_domain_sale_items(self, additional_domain=None):
        sale_items = self.sudo()._get_sale_order_items()
        domain = [
            ("order_id", "in", sale_items.sudo().order_id.ids),
            ("is_downpayment", "=", False),
            ("state", "=", "done"),
            ("display_type", "=", False),
            "|",
            ("project_id", "in", [*self.ids, False]),
            ("id", "in", sale_items.ids),
        ]
        if additional_domain:
            domain = Domain.AND([domain, additional_domain])
        return domain

    def _get_domain_from_section_id(self, section_id):
        return self._get_domain_sale_items(
            [("product_type", "!=" if section_id == "materials" else "=", "service")]
        )

    def _is_profitability_shown(self):
        self.check_singleton()
        return self.allow_billable and super()._is_profitability_shown()

    def _is_profitability_helper_shown(self):
        return True

    def _get_profitability_labels(self):
        return {
            **super()._get_profitability_labels(),
            "service_revenues": self.env._("Other Services"),
            "materials": self.env._("Materials"),
            "other_invoice_revenues": self.env._("Customer Invoices"),
            "downpayments": self.env._("Down Payments"),
            "cost_of_goods_sold": self.env._("Cost of Goods Sold"),
        }

    def _get_profitability_sequence_per_invoice_type(self):
        return {
            **super()._get_profitability_sequence_per_invoice_type(),
            "service_revenues": 6,
            "materials": 7,
            "other_invoice_revenues": 9,
            "downpayments": 20,
            "cost_of_goods_sold": 21,
        }

    def _get_service_policy_to_invoice_type(self):
        return {
            "ordered_prepaid": "service_revenues",
            "delivered_milestones": "service_revenues",
            "delivered_manual": "service_revenues",
        }

    def _get_domain_profitability_sale_order_items(self, domain=None):
        domain = Domain(domain or Domain.TRUE)
        return (
            Domain(
                [
                    "|",
                    ("product_id", "!=", False),
                    ("is_downpayment", "=", True),
                    ("is_expense", "=", False),
                    ("state", "=", "done"),
                    "|",
                    ("qty_to_invoice", ">", 0),
                    ("qty_invoiced", ">", 0),
                ]
            )
            & domain
        )

    def _get_revenues_items_from_sol(self, domain=None, with_action=True):
        sale_line_read_group = (
            self.env["sale.order.line"]
            .sudo()
            ._read_group(
                self._get_domain_profitability_sale_order_items(domain),
                ["currency_id", "product_id", "is_downpayment"],
                [
                    "id:array_agg",
                    "amount_taxexc_to_invoice:sum",
                    "amount_taxexc_invoiced:sum",
                ],
            )
        )
        display_sol_action = (
            with_action
            and len(self) == 1
            and self.env.user.has_group("sale.group_sale_salesman")
        )
        revenues_dict = {}
        total_to_invoice = total_invoiced = 0.0
        data = []
        sequence_per_invoice_type = self._get_profitability_sequence_per_invoice_type()
        if sale_line_read_group:
            convert_company = self.company_id or self.env.company

            sols_per_product = defaultdict(lambda: [0.0, 0.0, []])
            downpayment_amount_invoiced = 0
            downpayment_sol_ids = []
            for (
                currency,
                product,
                is_downpayment,
                sol_ids,
                amount_taxexc_to_invoice,
                amount_taxexc_invoiced,
            ) in sale_line_read_group:
                if is_downpayment:
                    downpayment_amount_invoiced += currency._convert(
                        amount_taxexc_invoiced,
                        convert_company.currency_id,
                        convert_company,
                        round=False,
                    )
                    downpayment_sol_ids += sol_ids
                else:
                    sols_per_product[product.id][0] += currency._convert(
                        amount_taxexc_to_invoice,
                        convert_company.currency_id,
                        convert_company,
                    )
                    sols_per_product[product.id][1] += currency._convert(
                        amount_taxexc_invoiced,
                        convert_company.currency_id,
                        convert_company,
                    )
                    sols_per_product[product.id][2] += sol_ids
            if downpayment_amount_invoiced:
                downpayments_data = {
                    "id": "downpayments",
                    "sequence": sequence_per_invoice_type["downpayments"],
                    "invoiced": downpayment_amount_invoiced,
                    "to_invoice": -downpayment_amount_invoiced,
                }
                if with_action and (
                    self.env.user.has_group("sale.group_sale_salesman_all_leads,")
                    or self.env.user.has_group("account.group_account_invoice,")
                    or self.env.user.has_group("account.group_account_readonly")
                ):
                    invoices = self.env["account.move"].search(
                        [("line_ids.sale_line_ids", "in", downpayment_sol_ids)]
                    )
                    args = ["downpayments", [("id", "in", invoices.ids)]]
                    if len(invoices) == 1:
                        args.append(invoices.id)
                    downpayments_data["action"] = {
                        "name": "action_profitability_items",
                        "type": "object",
                        "args": json.dumps(args),
                    }
                data += [downpayments_data]
                total_invoiced += downpayment_amount_invoiced
                total_to_invoice -= downpayment_amount_invoiced
            product_read_group = (
                self.env["product.product"]
                .sudo()
                ._read_group(
                    [("id", "in", list(sols_per_product))],
                    ["invoice_policy", "service_type", "type"],
                    ["id:array_agg"],
                )
            )
            service_policy_to_invoice_type = self._get_service_policy_to_invoice_type()
            general_to_service_map = self.env[
                "product.template"
            ]._get_general_to_service_map()
            for invoice_policy, service_type, type_, product_ids in product_read_group:
                service_policy = None
                if type_ == "service":
                    service_policy = general_to_service_map.get(
                        (invoice_policy, service_type), "ordered_prepaid"
                    )
                for product_id, (
                    amount_to_invoice,
                    amount_invoiced,
                    sol_ids,
                ) in sols_per_product.items():
                    if product_id in product_ids:
                        invoice_type = service_policy_to_invoice_type.get(
                            service_policy, "materials"
                        )
                        revenue = revenues_dict.setdefault(
                            invoice_type, {"invoiced": 0.0, "to_invoice": 0.0}
                        )
                        revenue["to_invoice"] += amount_to_invoice
                        total_to_invoice += amount_to_invoice
                        revenue["invoiced"] += amount_invoiced
                        total_invoiced += amount_invoiced
                        if display_sol_action and invoice_type in [
                            "service_revenues",
                            "materials",
                        ]:
                            revenue.setdefault("record_ids", []).extend(sol_ids)

            if display_sol_action:
                section_name = "materials"
                materials = revenues_dict.get(section_name, {})
                sale_order_items = (
                    self.env["sale.order.line"]
                    .browse(materials.pop("record_ids", []))
                    ._filtered_access("read")
                )
                if sale_order_items:
                    args = [section_name, [("id", "in", sale_order_items.ids)]]
                    if len(sale_order_items) == 1:
                        args.append(sale_order_items.id)
                    action_params = {
                        "name": "action_profitability_items",
                        "type": "object",
                        "args": json.dumps(args),
                    }
                    if len(sale_order_items) == 1:
                        action_params["res_id"] = sale_order_items.id
                    materials["action"] = action_params
        data += [
            {
                "id": invoice_type,
                "sequence": sequence_per_invoice_type[invoice_type],
                **vals,
            }
            for invoice_type, vals in revenues_dict.items()
        ]
        return {
            "data": data,
            "total": {"to_invoice": total_to_invoice, "invoiced": total_invoiced},
        }

    def _get_domain_items_from_invoices(self, domain=None):
        domain = Domain(domain or Domain.TRUE)
        included_invoice_line_ids = (
            self._get_already_included_profitability_invoice_line_ids()
        )
        return domain & Domain(
            [
                ("move_id.move_type", "in", self.env["account.move"].get_sale_types()),
                ("parent_state", "in", ["draft", "posted"]),
                ("price_subtotal", "!=", 0),
                ("is_downpayment", "=", False),
                ("id", "not in", included_invoice_line_ids),
            ]
        )

    def _get_items_from_invoices(self, excluded_move_line_ids=None, with_action=True):
        if excluded_move_line_ids is None:
            excluded_move_line_ids = []
        aml_fetch_fields = [
            "balance",
            "parent_state",
            "company_currency_id",
            "analytic_distribution",
            "move_id",
            "display_type",
            "date",
        ]
        invoices_move_lines = (
            self.env["account.move.line"]
            .sudo()
            .search_fetch(
                Domain.AND(
                    [
                        self._get_domain_items_from_invoices(
                            [("id", "not in", excluded_move_line_ids)]
                        ),
                        [("analytic_distribution", "in", self.account_id.ids)],
                    ]
                ),
                aml_fetch_fields,
            )
        )
        res = {
            "revenues": {"data": [], "total": {"invoiced": 0.0, "to_invoice": 0.0}},
            "costs": {"data": [], "total": {"billed": 0.0, "to_bill": 0.0}},
        }
        if invoices_move_lines:
            revenues_lines = []
            cogs_lines = []
            for move_line in invoices_move_lines:
                if move_line["display_type"] == "cogs":
                    cogs_lines.append(move_line)
                else:
                    revenues_lines.append(move_line)
            for move_lines, ml_type in (
                (revenues_lines, "revenues"),
                (cogs_lines, "costs"),
            ):
                amount_invoiced = amount_to_invoice = 0.0
                for move_line in move_lines:
                    currency = move_line.company_currency_id
                    line_balance = currency._convert(
                        move_line.balance,
                        self.currency_id,
                        self.company_id,
                        move_line.date,
                    )
                    analytic_contribution = (
                        sum(
                            percentage
                            for ids, percentage in move_line.analytic_distribution.items()
                            if str(self.account_id.id) in ids.split(",")
                        )
                        / 100.0
                    )
                    if move_line.parent_state == "draft":
                        amount_to_invoice -= line_balance * analytic_contribution
                    else:
                        amount_invoiced -= line_balance * analytic_contribution
                if amount_invoiced != 0 or amount_to_invoice != 0:
                    section_id = (
                        "other_invoice_revenues"
                        if ml_type == "revenues"
                        else "cost_of_goods_sold"
                    )
                    invoices_items = {
                        "id": section_id,
                        "sequence": self._get_profitability_sequence_per_invoice_type()[
                            section_id
                        ],
                        "invoiced"
                        if ml_type == "revenues"
                        else "billed": amount_invoiced,
                        "to_invoice"
                        if ml_type == "revenues"
                        else "to_bill": amount_to_invoice,
                    }
                    if with_action and (
                        self.env.user.has_group("sale.group_sale_salesman_all_leads")
                        or self.env.user.has_group("account.group_account_invoice")
                        or self.env.user.has_group("account.group_account_readonly")
                    ):
                        invoices_items["action"] = (
                            self._get_action_for_profitability_section(
                                invoices_move_lines.move_id.ids, section_id
                            )
                        )
                    res[ml_type] = {
                        "data": [invoices_items],
                        "total": {
                            "invoiced"
                            if ml_type == "revenues"
                            else "billed": amount_invoiced,
                            "to_invoice"
                            if ml_type == "revenues"
                            else "to_bill": amount_to_invoice,
                        },
                    }
        return res

    def _add_invoice_items(self, domain, profitability_items, with_action=True):
        sale_lines = (
            self.env["sale.order.line"]
            .sudo()
            ._read_group(
                self._get_domain_profitability_sale_order_items(domain),
                [],
                ["id:recordset"],
            )[0][0]
        )
        items_from_invoices = self._get_items_from_invoices(
            excluded_move_line_ids=sale_lines.invoice_line_ids.ids,
            with_action=with_action,
        )
        profitability_items["revenues"]["data"] += items_from_invoices["revenues"][
            "data"
        ]
        profitability_items["revenues"]["total"]["to_invoice"] += items_from_invoices[
            "revenues"
        ]["total"]["to_invoice"]
        profitability_items["revenues"]["total"]["invoiced"] += items_from_invoices[
            "revenues"
        ]["total"]["invoiced"]
        profitability_items["costs"]["data"] += items_from_invoices["costs"]["data"]
        profitability_items["costs"]["total"]["to_bill"] += items_from_invoices[
            "costs"
        ]["total"]["to_bill"]
        profitability_items["costs"]["total"]["billed"] += items_from_invoices["costs"][
            "total"
        ]["billed"]

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        sale_items = self.sudo()._get_sale_order_items()
        domain = [
            ("order_id", "in", sale_items.order_id.ids),
            "|",
            "|",
            ("project_id", "in", self.ids),
            ("project_id", "=", False),
            ("id", "in", sale_items.ids),
        ]
        revenue_items_from_sol = self._get_revenues_items_from_sol(
            domain,
            with_action,
        )
        profitability_items["revenues"]["data"] += revenue_items_from_sol["data"]
        profitability_items["revenues"]["total"]["to_invoice"] += (
            revenue_items_from_sol["total"]["to_invoice"]
        )
        profitability_items["revenues"]["total"]["invoiced"] += revenue_items_from_sol[
            "total"
        ]["invoiced"]
        self._add_invoice_items(domain, profitability_items, with_action=with_action)
        return profitability_items

    def _get_stat_buttons(self):
        buttons = super()._get_stat_buttons()
        if self.env.user.has_group("sale.group_sale_salesman_all_leads"):
            buttons.append(
                {
                    "icon": "dollar",
                    "text": self.env._("Sales Orders"),
                    "number": self.sale_order_count,
                    "action_type": "object",
                    "action": "action_view_sos",
                    "additional_context": json.dumps(
                        {
                            "create_for_project_id": self.id,
                        }
                    ),
                    "show": self.display_sales_stat_buttons
                    and self.sale_order_count > 0,
                    "sequence": 27,
                }
            )
            buttons.append(
                {
                    "icon": "dollar",
                    "text": self.env._("Sales Order Items"),
                    "number": self.sale_order_line_count,
                    "action_type": "object",
                    "action": "action_view_sols",
                    "show": self.display_sales_stat_buttons,
                    "sequence": 28,
                }
            )
        if self.env.user.has_group("account.group_account_readonly"):
            buttons.append(
                {
                    "icon": "pencil-square-o",
                    "text": self.env._("Invoices"),
                    "number": self.invoice_count,
                    "action_type": "object",
                    "action": "action_view_project_invoices",
                    "show": bool(self.account_id) and self.invoice_count > 0,
                    "sequence": 30,
                }
            )
        if self.env.user.has_group("account.group_account_readonly"):
            buttons.append(
                {
                    "icon": "pencil-square-o",
                    "text": self.env._("Vendor Bills"),
                    "number": self.vendor_bill_count,
                    "action_type": "object",
                    "action": "action_view_project_vendor_bills",
                    "show": self.vendor_bill_count > 0,
                    "sequence": 38,
                }
            )
        return buttons

    def _get_profitability_values(self):
        if not self.allow_billable:
            return {}, False
        return super()._get_profitability_values()

    def _get_domain_projects_to_make_billable(self):
        return Domain.AND(
            [
                super()._get_domain_projects_to_make_billable(),
                [("allow_billable", "=", False)],
            ]
        )

    def action_view_tasks(self):
        if self.env.context.get("generate_milestone"):
            line_id = self.env.context.get("default_sale_line_id")
            default_line = self.env["sale.order.line"].browse(line_id)
            milestone = self.env["project.milestone"].create(
                {
                    "name": default_line.name,
                    "project_id": self.id,
                    "sale_line_id": line_id,
                    "quantity_percentage": 1,
                }
            )
            if default_line.product_id.service_tracking == "task_in_project":
                default_line.task_id.milestone_id = milestone.id

        action = super().action_view_tasks()
        action["context"]["hide_partner"] = self._is_partner_hidden()
        action["context"]["allow_billable"] = self.allow_billable
        if self.env.context.get("from_sale_order_action"):
            context = dict(action.get("context", {}))
            context.pop("search_default_open_tasks", None)
            if (
                sale_order_id := self.env.context.get(
                    "default_reinvoiced_sale_order_id"
                )
                or self.reinvoiced_sale_order_id.id
            ):
                context["search_default_sale_order_id"] = sale_order_id
            if not self.sale_order_id:
                sale_order = self.env["sale.order"].browse(
                    self.env.context.get("active_id")
                )
                context["default_sale_order_id"] = sale_order.id
            action["context"] = context
        return action

    def action_view_project_vendor_bills(self):
        move_lines = self.env["account.move.line"].search_fetch(
            [
                ("move_id.move_type", "in", ["in_invoice", "in_refund"]),
                ("analytic_distribution", "in", self.account_id.ids),
            ],
            ["move_id"],
        )
        vendor_bill_ids = move_lines.move_id.ids
        action_window = {
            "name": _("Vendor Bills"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "views": [[False, "list"], [False, "form"], [False, "kanban"]],
            "domain": [("id", "in", vendor_bill_ids)],
            "context": {
                "default_move_type": "in_invoice",
                "project_id": self.id,
            },
            "help": "<p class='o_view_nocontent_smiling_face'>%s</p><p>%s</p>"
            % (
                _("Create a vendor bill"),
                _(
                    "Create invoices, register payments and keep track of the discussions with your vendors."
                ),
            ),
        }
        if (
            not self.env.context.get("from_embedded_action")
            and len(vendor_bill_ids) == 1
        ):
            action_window["views"] = [[False, "form"]]
            action_window["res_id"] = vendor_bill_ids[0]
        return action_window

    def _get_products_linked_to_template(self, limit=None):
        self.check_singleton()
        return self.env["product.template"].search(
            [("project_template_id", "=", self.id)], limit=limit
        )

    def action_confirm_template_to_project(self, callbacks):
        super().action_confirm_template_to_project(callbacks)
        if callbacks.get("unlink_template_products"):
            self._get_products_linked_to_template().project_template_id = False

    def _get_template_to_project_confirmation_callbacks(self):
        callbacks = super()._get_template_to_project_confirmation_callbacks()
        if self._get_products_linked_to_template(limit=1):
            callbacks["unlink_template_products"] = True
        return callbacks

    def _get_template_to_project_warnings(self):
        self.check_singleton()
        res = super()._get_template_to_project_warnings()
        if self.is_template and self._get_products_linked_to_template(limit=1):
            res.append(
                self.env._(
                    "Converting this template to a regular project will unlink it from its associated products."
                )
            )
        return res

    def _get_template_default_context_whitelist(self):
        return [
            *super()._get_template_default_context_whitelist(),
            "allow_billable",
            "from_sale_order_action",
        ]
