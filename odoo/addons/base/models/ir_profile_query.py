# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import psycopg2

from odoo import api, fields, models
from odoo.tools.speedscope import shorten
from odoo.tools.sql import format_query
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class IrProfileQuery(models.Model):
    _name = 'ir.profile.query'
    _description = 'Profiling Query'
    _log_access = False  # avoid useless foreign key on res_user
    _order = 'id asc'
    _rec_name = 'query_preview'
    _allow_sudo_commands = False

    profile_id = fields.Many2one('ir.profile', required=True, ondelete='cascade', index=True, readonly=True)
    time = fields.Float(string="Time", help="Time spent executing the query (seconds)", readonly=True, min_display_digits=6)
    query = fields.Text(readonly=True, help="Query with placeholders, before injecting the parameters")
    full_query = fields.Text(required=True, prefetch=False, readonly=True, help="Query with its parameters injected, ready to execute")
    query_preview = fields.Text(compute='_compute_query_preview')
    formatted_query = fields.Text(compute='_compute_formatted_query')
    plan = fields.Text('Query Plan', prefetch=False, readonly=True)

    @api.depends('query')
    def _compute_query_preview(self):
        for query in self:
            query.query_preview = shorten(query.query)

    @api.depends('full_query')
    def _compute_formatted_query(self):
        for query in self:
            if query.full_query:
                query.formatted_query = format_query(query.full_query)
            else:
                query.formatted_query = False

    def action_explain_analyse(self):
        for query in self:
            query._explain_analyse_one()

    def _explain_analyse_one(self):
        self.ensure_one()
        if not self.env.user._is_system():
            raise AccessError(self.env._("You are not allowed to generate a query plan."))

        _logger.info("User #%s is generating query plan for ir.profile.query %s", self.env.user.id, self.id)
        # Refuse stacked statements ("SELECT 1;DROP...;COMMIT") which escape
        # EXPLAIN. Naive on purpose (not aware of string literals or comments).
        if ';' in self.full_query.strip().removesuffix(';'):
            raise UserError(self.env._("This query cannot be explained."))
        try:
            with self.env.cr.savepoint() as savepoint:
                # full_query is raw SQL and really executes: the savepoint
                # rollback below is what makes this safe, don't drop it.
                query = f'EXPLAIN (ANALYZE, COSTS, VERBOSE, BUFFERS) {self.full_query}'
                self.env.cr.execute(query, log_exceptions=False)  # pylint: disable=sql-injection
                plan = '\n'.join(row[0] for row in self.env.cr.fetchall())
                savepoint.rollback()  # do not remove: discards the query's writes
        except psycopg2.Error as e:
            # Not everything can be explained:
            # SAVEPOINT/RELEASE/SET/LOCK/... are in the profile, which EXPLAIN rejects
            # with a psycopg2.errors.SyntaxError.
            raise UserError(self.env._("This query cannot be explained.")) from e
        self.plan = plan
