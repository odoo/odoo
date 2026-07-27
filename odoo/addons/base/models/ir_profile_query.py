# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import reprlib

import psycopg2

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

shortener = reprlib.Repr()
shortener.maxstring = 150
shorten = shortener.repr


class IrProfileQuery(models.Model):
    _name = 'ir.profile.query'
    _description = 'Profiling Query'
    _log_access = False  # avoid useless foreign key on res_user
    _order = 'sequence, id'
    _allow_sudo_commands = False

    sequence = fields.Integer(readonly=True)
    profile_id = fields.Many2one('ir.profile', required=True, ondelete='cascade', index=True, readonly=True)

    query = fields.Text(readonly=True,
        help="Query with placeholders, before injecting the parameters")
    full_query = fields.Text(required=True, prefetch=False, readonly=True, help="Query with its parameters injected, ready to execute")
    query_preview = fields.Text(compute='_compute_query_preview')
    start = fields.Float(help="Time at which the query started, relative to the profile", readonly=True)
    time = fields.Float(string="Time (seconds)", help="Time spent executing the query", readonly=True, min_display_digits=6)
    stack = fields.Json(prefetch=False, readonly=True)
    exec_context = fields.Json("Execution Context", prefetch=False, readonly=True)

    plan = fields.Text('Query Plan', prefetch=False, readonly=True)
    plan_url = fields.Text(compute='_compute_plan_url', readonly=True)

    @api.depends('plan')
    def _compute_plan_url(self):
        for query in self:
            if query.plan:
                query.plan_url = f'/web/query_plan/{query.id}'
            else:
                query.plan_url = False

    @api.depends('query')
    def _compute_query_preview(self):
        for query in self:
            query.query_preview = shorten(query.query)

    @api.depends('query_preview')
    def _compute_display_name(self):
        for query in self:
            query.display_name = query.query_preview

    def action_explain_analyse(self):
        if not self.env.user._is_system():
            raise AccessError(_("You are not allowed to generate a query plan."))
        self.ensure_one()
        _logger.info("Generating query plan for query %s", self.id)
        try:
            with self.env.cr.savepoint() as sp:
                # Not everything can be explained:
                # SAVEPOINT/RELEASE/SET/LOCK/... are in the profile, which EXPLAIN rejects
                # with a psycopg2.errors.SyntaxError.
                # pylint: disable=E8501
                self.env.cr.execute(
                    f'EXPLAIN (ANALYZE, COSTS, VERBOSE, BUFFERS, FORMAT JSON) {self.full_query}',
                    log_exceptions=False,
                )
                plan = self.env.cr.fetchone()[0]
                sp.rollback()
        except psycopg2.Error as e:
            raise UserError(_("This query cannot be explained.")) from e
        self.plan = json.dumps(plan)
        return self.action_open_plan_visualizer()

    def action_open_plan_visualizer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.plan_url,
            'target': 'new',
        }
