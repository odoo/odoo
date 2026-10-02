# Copyright 2022 Quartile
# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date, timedelta
from itertools import groupby

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class CommissionMakeSettle(models.TransientModel):
    _name = "commission.make.settle"
    _description = "Wizard for settling commissions"

    date_to = fields.Date("Up to", required=True, default=fields.Date.today)
    agent_ids = fields.Many2many(
        comodel_name="res.partner", domain="[('agent', '=', True)]"
    )
    settlement_type = fields.Selection(selection=[], required=True)
    can_settle = fields.Boolean(
        compute="_compute_can_settle",
        help="Technical field for improving UX when no extra *commission is installed.",
    )

    @api.depends("date_to")  # use this unrelated field to trigger the computation
    def _compute_can_settle(self):
        """Check if there's any settlement type for making the settlements."""
        self.can_settle = bool(
            self.env[self._name]._fields["settlement_type"].selection
        )

    def _get_period_start(self, agent, date_to):
        if agent.settlement == "monthly":
            return date(month=date_to.month, year=date_to.year, day=1)
        elif agent.settlement == "biweekly":
            if date_to.day >= 16:
                return date(month=date_to.month, year=date_to.year, day=16)
            else:
                return date(month=date_to.month, year=date_to.year, day=1)
        elif agent.settlement == "quaterly":
            # Get first month of the date quarter
            month = (date_to.month - 1) // 3 * 3 + 1
            return date(month=month, year=date_to.year, day=1)
        elif agent.settlement == "semi":
            if date_to.month > 6:
                return date(month=7, year=date_to.year, day=1)
            else:
                return date(month=1, year=date_to.year, day=1)
        elif agent.settlement == "annual":
            return date(month=1, year=date_to.year, day=1)
        elif agent.settlement == "pending":
            return date(month=date_to.month, year=date_to.year, day=date_to.day)

    def _get_next_period_date(self, agent, current_date):
        if agent.settlement == "monthly":
            return current_date + relativedelta(months=1)
        elif agent.settlement == "biweekly":
            if current_date.day == 1:
                return current_date + relativedelta(days=15)
            else:
                return date(
                    month=current_date.month, year=current_date.year, day=1
                ) + relativedelta(months=1, days=-1)
        elif agent.settlement == "quaterly":
            return current_date + relativedelta(months=3)
        elif agent.settlement == "semi":
            return current_date + relativedelta(months=6)
        elif agent.settlement == "annual":
            return current_date + relativedelta(years=1)
        elif agent.settlement == "pending":
            return date(
                month=self.date_to.month, year=self.date_to.year, day=self.date_to.day
            )

    def _get_settlement(self, agent, company, currency, sett_from, sett_to):
        self.ensure_one()
        return self.env["commission.settlement"].search(
            [
                ("agent_id", "=", agent.id),
                ("date_from", "=", sett_from),
                ("date_to", "=", sett_to),
                ("company_id", "=", company.id),
                ("currency_id", "=", currency.id),
                ("state", "=", "settled"),
                ("settlement_type", "=", self.settlement_type),
            ],
            limit=1,
        )

    def _prepare_settlement_vals(self, agent, company, sett_from, sett_to):
        return {
            "agent_id": agent.id,
            "date_from": sett_from,
            "date_to": sett_to,
            "company_id": company.id,
            "settlement_type": self.settlement_type,
        }

    def _prepare_settlement_line_vals(self, settlement, line):
        """Hook for returning the settlement line dictionary vals."""
        return {
            "settlement_id": settlement.id,
        }

    def _get_agent_lines(self, agent, date_to_agent):
        """Need to be extended according to settlement_type."""
        raise NotImplementedError()

    @api.model
    def _agent_lines_groupby(self, agent_line):
        return agent_line.company_id, agent_line.currency_id

    @api.model
    def _agent_lines_sorted(self, agent_line):
        return agent_line.company_id.id, agent_line.currency_id.id

    def action_settle(self):
        self.ensure_one()
        settlement_obj = self.env["commission.settlement"]
        settlement_line_obj = self.env["commission.settlement.line"]
        settlement_ids = []
        agents = self.agent_ids or self.env["res.partner"].search(
            [("agent", "=", True)]
        )
        date_to = self.date_to
        settlement_line_vals = []
        for agent in agents:
            date_to_agent = self._get_period_start(agent, date_to)
            # Get non settled elements
            grouped_agent_lines = groupby(
                sorted(
                    self._get_agent_lines(agent, date_to_agent),
                    key=self._agent_lines_sorted,
                ),
                key=self._agent_lines_groupby,
            )
            for _k, grouper_agent_lines in grouped_agent_lines:
                agent_lines = list(grouper_agent_lines)
                pos = 0
                sett_to = date(year=1900, month=1, day=1)
                settlement_line_vals = []
                while pos < len(agent_lines):
                    line = agent_lines[pos]
                    pos += 1
                    if line._skip_settlement():
                        continue
                    if line.invoice_date > sett_to:
                        sett_from = self._get_period_start(agent, line.invoice_date)
                        sett_to = self._get_next_period_date(agent, sett_from)
                        sett_to -= timedelta(days=1)
                        settlement = self._get_settlement(
                            agent, line.company_id, line.currency_id, sett_from, sett_to
                        )
                        if not settlement:
                            settlement = settlement_obj.create(
                                self._prepare_settlement_vals(
                                    agent,
                                    line.company_id,
                                    sett_from,
                                    sett_to,
                                )
                            )
                            settlement.currency_id = line.currency_id
                        settlement_ids.append(settlement.id)
                    settlement_line_vals.append(
                        self._prepare_settlement_line_vals(settlement, line)
                    )
                settlement_line_obj.create(settlement_line_vals)
        # go to results
        if len(settlement_ids):
            return {
                "name": _("Created Settlements"),
                "type": "ir.actions.act_window",
                "views": [[False, "list"], [False, "form"]],
                "res_model": "commission.settlement",
                "domain": [["id", "in", settlement_ids]],
            }
