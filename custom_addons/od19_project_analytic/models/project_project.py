from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = "project.project"

    job_no = fields.Char(
        string="Job Number",
        copy=False,
        tracking=True,
        index=True,
        help="Job number generated from department + project type + sales "
             "initials + year + running number. Required at the UI level but "
             "optional at the model level so core modules (e.g. sale_project) "
             "can still create projects.",
    )
    od19_department_id = fields.Many2one(
        "hr.department",
        string="Department",
        tracking=True,
        index=True,
        ondelete="restrict",
        help="Owning department. Drives the department-based document "
             "sequence and department-level reporting.",
    )
    project_owner_id = fields.Many2one(
        "res.partner",
        string="Project Owner",
        tracking=True,
        domain="[('od19_is_project_owner', '=', True)]",
    )
    contractor_ids = fields.Many2many(
        "res.partner",
        "project_contractor_rel",
        "project_id",
        "partner_id",
        string="Contractors",
        domain="[('od19_is_contractor', '=', True)]",
    )

    _job_no_unique = models.Constraint(
        "unique(job_no)",
        "Job Number must be unique.",
    )

    @api.constrains("job_no")
    def _check_job_no_uniqueness(self):
        for project in self:
            if project.job_no:
                duplicate = self.search(
                    [("job_no", "=", project.job_no), ("id", "!=", project.id)],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError("Job Number must be unique.")

    @api.constrains("project_owner_id")
    def _check_project_owner_role(self):
        for project in self:
            if (
                project.project_owner_id
                and not project.project_owner_id.od19_is_project_owner
            ):
                raise ValidationError(
                    "Project owner must have the Project Owner role."
                )

    @api.constrains("contractor_ids")
    def _check_contractor_roles(self):
        for project in self:
            invalid = project.contractor_ids.filtered(
                lambda p: not p.od19_is_contractor
            )
            if invalid:
                raise ValidationError(
                    "All contractors must have the Contractor role."
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("job_no"):
                duplicate = self.search(
                    [("job_no", "=", vals.get("job_no"))], limit=1
                )
                if duplicate:
                    raise ValidationError("Job Number must be unique.")
            if not vals.get("account_id"):
                vals["account_id"] = self._create_analytic_account(vals).id
        return super().create(vals_list)

    def _create_analytic_account(self, vals=None):
        # Keep the core contract (no arguments): core modules (hr_timesheet,
        # sale_project, ...) call this on a recordset to batch-create and
        # assign account_id. Only use the custom single-project path when the
        # caller passes explicit vals (see create() below).
        if vals is None:
            return super()._create_analytic_account()
        analytic_name = vals.get("job_no") or vals.get("name") or "Project"
        analytic = self.env["account.analytic.account"].create(
            {
                "name": analytic_name,
                "plan_id": self._get_default_analytic_plan_id(),
            }
        )
        return analytic

    @api.model
    def _get_default_analytic_plan_id(self):
        plan = self.env["account.analytic.plan"].search(
            [("name", "=", "Projects")], limit=1
        )
        if not plan:
            plan = self.env["account.analytic.plan"].search([], limit=1)
        return plan.id if plan else False

    def _od19_get_pnl_values(self, date_from=None, date_to=None, company_ids=None):
        """Return project P&L values read from posted analytic lines.

        Single P&L contract for the whole domain (spec 6.6): revenue/cost are
        derived from account.analytic.line.analytic_profitability, which Odoo 19
        computes from the general account type. Never re-implement the
        revenue/cost classification here.

        Lives in this module (the shared project/analytic base) so both the
        project P&L/risk reports (od19_project_enhanced) and the sale-order
        cost & profit analysis wizard (od19_sales_project_context) reuse the
        same contract without a heavyweight dependency between them.
        """
        self.ensure_one()
        company_ids = company_ids or self.env.companies.ids
        result = {
            "analytic_account_id": self.account_id.id or False,
            "has_analytic": bool(self.account_id),
            "revenue": 0.0,
            "cost": 0.0,
            "gross_margin": 0.0,
            "margin_percent": 0.0,
            "uncategorized_amount": 0.0,
        }
        if not self.account_id:
            return result
        base_domain = [
            ("account_id", "=", self.account_id.id),
            ("company_id", "in", list(company_ids)),
            ("move_line_id", "!=", False),
            ("move_line_id.parent_state", "=", "posted"),
        ]
        if date_from:
            base_domain.append(("date", ">=", date_from))
        if date_to:
            base_domain.append(("date", "<=", date_to))

        def _sum(profitability):
            lines = self.env["account.analytic.line"].search(
                base_domain + [("analytic_profitability", "in", [profitability])]
            )
            return sum(lines.mapped("amount"))

        revenue = _sum("revenue")
        cost = -_sum("loss")
        result.update(
            revenue=revenue,
            cost=cost,
            gross_margin=revenue - cost,
            margin_percent=(revenue - cost) / revenue * 100.0 if revenue else 0.0,
            uncategorized_amount=_sum("uncategorized"),
        )
        return result
