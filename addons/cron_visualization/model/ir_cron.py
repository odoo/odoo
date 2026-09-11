# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class IrCron(models.Model):
    _inherit = 'ir.cron'

    # Don't store data related to the history. The cursor crash when storing data.
    cv_ir_cron_history_ids = fields.One2many('cv.ir.cron.history', 'ir_cron_id', string='Cron History')
    cv_history_count = fields.Integer(string='History Count', compute='_compute_history_count')

    next_execution_timer = fields.Float(string='Next Execution Timer', compute='_compute_next_execution_timer', help='Time remaining before the next execution')

    is_running = fields.Boolean(string='Is Running', compute='_compute_is_running', search='_search_is_running', help='Is the cron currently running')
    progress_estimated = fields.Char(string='Progress Estimated', compute='_compute_progress_estimated', help='Current progress of the cron (progress;duration;type)')
    history = fields.Char(string='History',  compute='_compute_history', help='History of the last 10 runs (state;duration)')

    def _compute_next_execution_timer(self):
        for cron in self:
            if cron.nextcall:
                next_execution_timer = (cron.nextcall - fields.Datetime.now()).total_seconds() / 60
                cron.next_execution_timer = next_execution_timer
            else:
                cron.next_execution_timer = False

    def _compute_history_count(self):
        for cron in self:
            cron.cv_history_count = len(cron.cv_ir_cron_history_ids)

    def open_history(self):
        """ Keep in sync with cv_ir_cron_history_action. """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cron History'),
            'res_model': 'cv.ir.cron.history',
            'view_mode': 'tree,pivot,graph,calendar,form',
            'domain': [('ir_cron_id', '=', self.id)],
            'context': {'graph_groupbys': ['started_at:day', 'state']},
            'help': _('<p class="o_view_nocontent_empty_folder">No history found!</p>'),
        }

    def _compute_is_running(self):
        """ Check history to know if cron is running. """
        for cron in self:
            cron.is_running = len(cron.cv_ir_cron_history_ids.filtered(lambda h: h.state == 'running')) > 0

    def _search_is_running(self, operator, value):
        """ Check history to know if cron is running. """
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        if operator != '=':
            value = not value
        self._cr.execute("""
            SELECT id FROM ir_cron
            WHERE id IN (
                SELECT ir_cron_id
                FROM cv_ir_cron_history
                WHERE state = 'running'
            )
        """)
        return [('id', 'in' if value else 'not in', [r[0] for r in self._cr.fetchall()])]

    def _compute_progress_estimated(self):
        """ Check history to estimate the progress of the current run. """
        for cron in self:
            if not cron.cv_ir_cron_history_ids or not cron.is_running:
                cron.progress_estimated = False
                continue
            avg_sql = """
                SELECT AVG(duration) AS average_duration
                FROM (
                    SELECT ir_cron_id, duration
                    FROM cv_ir_cron_history
                    WHERE state = 'success' AND ir_cron_id = %s
                    ORDER BY id DESC
                    LIMIT 10
                ) AS recent_success_records;
            """
            self.env.cr.execute(avg_sql, (cron.id,))
            average_duration = self.env.cr.fetchone()
            if not average_duration or not average_duration[0]:
                cron.progress_estimated = False
                continue
            running_sql = """
                SELECT started_at, type
                FROM cv_ir_cron_history
                WHERE state = 'running' AND ir_cron_id = %s
                ORDER BY started_at;
            """
            self.env.cr.execute(running_sql, (cron.id,))
            running_sql = self.env.cr.fetchall()
            if not running_sql:
                cron.progress_estimated = False
                continue
            progress_estimated = []
            for history in running_sql:
                duration = (fields.Datetime.now() - history[0]).total_seconds() / 60
                if average_duration[0] > 0:
                    progress = min(99, round(duration / average_duration[0] * 100, 2))
                    progress_estimated.append(str(progress) + ';' + str(duration) + ';' + history[1])
                else:
                    progress_estimated.append('99;' + str(duration) + ';' + history[1])
            if progress_estimated:
                cron.progress_estimated = ','.join(progress_estimated)
            else:
                cron.progress_estimated = False

            # sql = """
            #     with avgerage as (
            #         SELECT AVG(duration) AS average_duration
            #         FROM (
            #             SELECT ir_cron_id, duration
            #             FROM cv_ir_cron_history
            #             WHERE state = 'success' AND ir_cron_id = %s
            #             ORDER BY id DESC
            #             LIMIT 10
            #         ) AS recent_success_records
            #     )
            #
            #     SELECT
            #         COALESCE(
            #             STRING_AGG(
            #                 CASE
            #                     WHEN avgerage.average_duration > 0 THEN LEAST(99, ROUND(CAST(running_since / avgerage.average_duration * 100 AS numeric), 2)) || ';' || running_since || ';' || htype
            #                     ELSE '99;' || running_since || ';' || htype
            #                 END,
            #                 ','
            #             ),
            #             NULL
            #         ) AS progress_estimated
            #     FROM (
            #         SELECT
            #             h.id,
            #             h.ir_cron_id,
            #             h.type as htype,
            #             (EXTRACT(EPOCH FROM (NOW() - h.started_at)) / 60) AS running_since
            #         FROM cv_ir_cron_history AS h
            #         WHERE h.state = 'running' AND h.ir_cron_id = %s
            #     ) AS cich
            #     join avgerage on 1 = 1;
            # """
            # self.env.cr.execute(sql, (cron.id, cron.id))
            # result = self.env.cr.fetchone()
            # if result:
            #     cron.progress_estimated = result[0]

    def _compute_history(self):
        for cron in self:
            if not cron.cv_ir_cron_history_ids:
                cron.history = ''
                continue
            res = []
            for history in cron.cv_ir_cron_history_ids[:10]:
                res.insert(0, '{};{}'.format(history.state, history.duration))
            cron.history = ','.join(res)

    def method_direct_trigger(self):
        """ Override the method to setup is_running. """
        history = self.env['cv.ir.cron.history'].create({'ir_cron_id': self.id, 'type': 'manual'})
        self.env.cr.commit()
        try:
            return super().method_direct_trigger()
        except Exception as e:
            self.env.cr.rollback()
            history.finish(False, str(e))
            self.env.cr.commit()
            raise e
        finally:
            history.finish(True)

    @api.model
    def _callback(self, cron_name, server_action_id, job_id):
        """ Override the method to setup is_running. """
        history = self.env['cv.ir.cron.history'].create({'ir_cron_id': job_id, 'type': 'automatic'})
        self.env.cr.commit()
        super()._callback(cron_name, server_action_id, job_id)
        if history.ended_at is False:
            history.finish(True)

    @api.model
    def _handle_callback_exception(self, cron_name, server_action_id, job_id, job_exception):
        super()._handle_callback_exception(cron_name, server_action_id, job_id, job_exception)
        history = self.env['cv.ir.cron.history'].search([
            ('ir_cron_id', '=', job_id), ('user_id', '=', self.env.user.id), ('type', '=', 'automatic')
        ], limit=1, order='id DESC')
        history.finish(False, str(job_exception))
