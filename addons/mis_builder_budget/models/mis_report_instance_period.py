# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

SRC_MIS_BUDGET = "mis_budget"
SRC_MIS_BUDGET_BY_ACCOUNT = "mis_budget_by_account"


class MisReportInstancePeriod(models.Model):
    _inherit = "mis.report.instance.period"

    source = fields.Selection(
        selection_add=[
            (SRC_MIS_BUDGET, "MIS Budget by KPI"),
            (SRC_MIS_BUDGET_BY_ACCOUNT, "MIS Budget by Account"),
        ],
        ondelete={
            SRC_MIS_BUDGET: "cascade",
            SRC_MIS_BUDGET_BY_ACCOUNT: "cascade",
        },
    )
    source_mis_budget_id = fields.Many2one(
        comodel_name="mis.budget", string="Budget by KPI"
    )
    source_mis_budget_by_account_id = fields.Many2one(
        comodel_name="mis.budget.by.account", string="Budget by Account"
    )

    @api.depends("source")
    def _compute_source_aml_model_id(self):
        for record in self:
            if record.source == SRC_MIS_BUDGET:
                record.source_aml_model_id = False
            elif record.source == SRC_MIS_BUDGET_BY_ACCOUNT:
                record.source_aml_model_id = (
                    self.env["ir.model"]
                    .sudo()
                    .search([("model", "=", "mis.budget.by.account.item")])
                )
        return super()._compute_source_aml_model_id()

    def _get_additional_move_line_filter(self):
        domain = super()._get_additional_move_line_filter()
        if self.source == SRC_MIS_BUDGET_BY_ACCOUNT:
            domain.extend([("budget_id", "=", self.source_mis_budget_by_account_id.id)])
        return domain

    def _get_additional_budget_item_filter(self):
        """Prepare a filter to apply on all budget items

        This filter is applied with a AND operator on all
        budget items. This hook is intended
        to be inherited, and is useful to implement filtering
        on analytic dimensions or operational units.

        The default filter is built from a ``mis_report_filters context``
        key, which is a list set by the analytic filtering mechanism
        of the mis report widget::

          [(field_name, {'value': value, 'operator': operator})]

        This default filter is the same as the one set by
        _get_additional_move_line_filter on mis.report.instance.period, so
        a budget.item is expected to have the same analytic fields as
        a move line.

        Returns an Odoo domain expression (a python list)
        compatible with mis.budget.item."""
        self.ensure_one()
        filters = self._get_additional_move_line_filter()
        return filters
