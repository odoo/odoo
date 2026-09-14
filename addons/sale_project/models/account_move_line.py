from odoo import models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_analytic_distribution(self):
        project_amls = self.filtered(
            lambda aml: aml.analytic_distribution and any(aml.sale_line_ids.project_id)
        )
        super(AccountMoveLine, self - project_amls)._compute_analytic_distribution()
        project_id = self.env.context.get("project_id", False)
        if project_id:
            project = self.env["project.project"].browse(project_id)
            lines = self.filtered(
                lambda line: (
                    line.account_type not in ["asset_receivable", "liability_payable"]
                )
            )
            _debug.logic("analytic_from_context_project", lines=lines, project=project)
            lines.analytic_distribution = project._get_analytic_distribution()

    def _get_domain_so_mapping(self):
        return Domain.OR(
            Domain.AND(
                Domain(
                    self.env["account.analytic.account"]
                    .browse(int(account_id))
                    .root_plan_id._column_name(),
                    "=",
                    int(account_id),
                )
                for account_id in key.split(",")
            )
            for line in self
            for key in line.analytic_distribution or []
        )

    def _get_so_mapping_from_project(self):
        mapping = {}
        projects = self.env["project.project"].search(
            domain=self._get_domain_so_mapping()
        )
        orders_per_project = dict(
            self.env["sale.order"]._read_group(
                domain=[("project_id", "in", projects.ids)],
                groupby=["project_id"],
                aggregates=["id:recordset"],
            )
        )
        project_per_accounts = {
            next(iter(project._get_analytic_distribution())): project
            for project in projects
        }

        for move_line in self:
            analytic_distribution = move_line.analytic_distribution
            if not analytic_distribution:
                continue

            project = None
            for accounts in analytic_distribution:
                project = project_per_accounts.get(accounts)
                if project:
                    break
            if not project:
                continue

            orders = orders_per_project.get(project)
            if not orders:
                continue
            orders = orders.sorted("create_date")
            in_sale_state_orders = orders.filtered(lambda s: s.state == "done")

            mapping[move_line.id] = (
                in_sale_state_orders[0] if in_sale_state_orders else orders[0]
            )

        _debug.perf.count(
            "so_mapping_from_project",
            lines=len(self),
            projects=len(projects),
            mapped=len(mapping),
        )
        return mapping

    def _sale_get_order_map(self):
        mapping_from_invoice = super()._sale_get_order_map()
        mapping_from_invoice.update(self._get_so_mapping_from_project())
        return mapping_from_invoice
