import random
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

from ..tools import debug_log as dbg
from odoo.addons.project.models.project_task import DELIVERED_STATES


class ProjectForecastWizard(models.TransientModel):
    _name = "project.forecast.wizard"
    _description = "Monte Carlo Forecast"

    SIMULATION_WEEK_CAP = 200

    project_id = fields.Many2one(
        comodel_name="project.project",
        default=lambda self: self.env.context.get("active_id"),
        required=True,
    )
    remaining_items = fields.Integer(
        compute="_compute_remaining_items",
        store=True,
        readonly=False,
        help="Number of tasks to complete. Defaults to open task count.",
    )
    simulation_count = fields.Integer(
        string="Simulations",
        default=1000,
        help="Number of Monte Carlo iterations (more = more accurate).",
    )
    weeks_of_history = fields.Integer(
        string="Weeks of History",
        default=12,
        help="How many weeks of throughput data to sample from.",
    )
    p50_weeks = fields.Float(
        string="50th Percentile (weeks)",
        digits=(5, 1),
        readonly=True,
    )
    p85_weeks = fields.Float(
        string="85th Percentile (weeks)",
        digits=(5, 1),
        readonly=True,
    )
    p95_weeks = fields.Float(
        string="95th Percentile (weeks)",
        digits=(5, 1),
        readonly=True,
    )
    result_text = fields.Text(
        string="Forecast Summary",
        readonly=True,
    )

    @api.depends("project_id")
    def _compute_remaining_items(self) -> None:
        for wiz in self:
            if wiz.project_id:
                wiz.remaining_items = wiz.project_id.open_task_count
            else:
                wiz.remaining_items = 0

    @dbg.timed
    def action_run_forecast(self) -> dict:
        self.check_singleton()
        if self.simulation_count < 1:
            raise UserError(self.env._("The number of simulations must be at least 1."))
        sim_count = min(self.simulation_count, 100_000)
        dbg.lifecycle.debug(
            "project.forecast.wizard.action_run_forecast [project:%s]: remaining=%s "
            "sims=%s (requested %s) weeks=%s",
            self.project_id.id,
            self.remaining_items,
            sim_count,
            self.simulation_count,
            self.weeks_of_history,
        )
        if not self.remaining_items or self.remaining_items <= 0:
            self.result_text = "No remaining items to forecast."
            return self._prepare_action_reopen()

        throughput = self._get_weekly_throughput()
        dbg.logic.debug(
            "forecast [project:%s]: throughput series %s",
            self.project_id.id,
            throughput,
        )
        if not throughput or all(t == 0 for t in throughput):
            self.result_text = (
                "No historical throughput data available. "
                "Close some tasks to build forecasting data."
            )
            return self._prepare_action_reopen()

        results = []
        truncated = 0
        for _i in range(sim_count):
            weeks = 0
            remaining = self.remaining_items
            while remaining > 0:
                weekly_tp = random.choice(throughput)
                remaining -= max(weekly_tp, 0)
                weeks += 1
                if weeks >= self.SIMULATION_WEEK_CAP:
                    truncated += 1
                    break
            results.append(weeks)

        results.sort()
        n = len(results)
        self.p50_weeks = results[int(n * 0.50)]
        self.p85_weeks = results[int(n * 0.85)]
        self.p95_weeks = results[int(n * 0.95)]
        dbg.logic.debug(
            "forecast [project:%s]: p50=%s p85=%s p95=%s truncated=%d/%d",
            self.project_id.id,
            self.p50_weeks,
            self.p85_weeks,
            self.p95_weeks,
            truncated,
            sim_count,
        )

        avg_tp = sum(throughput) / len(throughput)
        lines = [
            self.env._(
                "Based on %(weeks)s weeks of throughput data (%(sims)s simulations):",
                weeks=len(throughput),
                sims=sim_count,
            ),
            "",
            self.env._(
                "  50%% chance of finishing in %(p)s weeks or less",
                p=f"{self.p50_weeks:.0f}",
            ),
            self.env._(
                "  85%% chance of finishing in %(p)s weeks or less",
                p=f"{self.p85_weeks:.0f}",
            ),
            self.env._(
                "  95%% chance of finishing in %(p)s weeks or less",
                p=f"{self.p95_weeks:.0f}",
            ),
            "",
            self.env._("Remaining items: %(n)s", n=self.remaining_items),
            self.env._(
                "Historical throughput: %(lo)s-%(hi)s tasks/week (avg %(avg)s), "
                "including %(zeros)s week(s) with no delivery",
                lo=min(throughput),
                hi=max(throughput),
                avg=f"{avg_tp:.1f}",
                zeros=sum(1 for t in throughput if not t),
            ),
        ]
        if truncated:
            lines += [
                "",
                self.env._(
                    "WARNING: %(pct)s%% of simulations had not finished after "
                    "%(cap)s weeks and were cut short — the percentiles above "
                    "are optimistic lower bounds.",
                    pct=f"{100 * truncated / sim_count:.0f}",
                    cap=self.SIMULATION_WEEK_CAP,
                ),
            ]
        self.result_text = "\n".join(lines)
        return self._prepare_action_reopen()

    @dbg.timed
    def _get_weekly_throughput(self) -> list[int]:
        self.project_id.check_access("read")
        since = self.env.cr.now() - timedelta(weeks=self.weeks_of_history)
        self.env.cr.execute(
            SQL(
                """
            WITH closed AS (
                    SELECT DATE_TRUNC('week', date_closed) AS week_start,
                           COUNT(*) AS closed_count
                      FROM project_task
                     WHERE project_id = %(project_id)s
                       AND state IN %(delivered_states)s
                       AND date_closed >= %(since)s
                       AND is_template IS NOT TRUE
                     GROUP BY DATE_TRUNC('week', date_closed)
            ),
            bounds AS (
                    SELECT GREATEST(
                               DATE_TRUNC('week', %(since)s::timestamp),
                               LEAST(
                                   DATE_TRUNC('week', %(project_start)s::timestamp),
                                   COALESCE(
                                       (SELECT MIN(week_start) FROM closed),
                                       DATE_TRUNC('week', %(project_start)s::timestamp)
                                   )
                               )
                           ) AS series_start
            )
            SELECT COALESCE(closed.closed_count, 0) AS closed_count
              FROM bounds,
                   generate_series(
                       bounds.series_start,
                       DATE_TRUNC('week', %(now)s::timestamp),
                       INTERVAL '1 week'
                   ) AS w(week_start)
              LEFT JOIN closed ON closed.week_start = w.week_start
             ORDER BY w.week_start
            """,
                project_id=self.project_id.id,
                delivered_states=DELIVERED_STATES,
                since=since,
                now=self.env.cr.now(),
                project_start=self.project_id.create_date or since,
            )
        )
        return [row[0] for row in self.env.cr.fetchall()]

    def _prepare_action_reopen(self) -> dict:
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
