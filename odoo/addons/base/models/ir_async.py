# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import itertools
import json
import logging
import re
import traceback
import threading
import odoo
import odoo.exceptions
from odoo import api, fields, models
from odoo.http import serialize_exception

_logger = logging.getLogger(__name__)
BASE_VERSION = odoo.modules.load_information_from_description_file('base')['version']


class IrAsync(models.Model):
    _name = 'ir.async'
    _description = 'Asynchronous Jobs'

    name = fields.Char()
    state = fields.Selection([
        ('created', 'Created'),     # The job has been enqueued for later processing
        ('succeeded', 'Succeeded'), # The job finished with a result, the result has not yet been retrieved
        ('failed', 'Failed'),       # The job failed due to an exception
        ('done', 'Done'),           # The job finished without result or the result has been retrieved
    ])
    res_model = fields.Char()
    res_ids = fields.Text()
    method = fields.Char()
    args = fields.Text()
    kwargs = fields.Text()
    user_id = fields.Many2one('res.users', string='Scheduler User', ondelete='cascade')
    context = fields.Text()
    super_user = fields.Boolean()
    traceback = fields.Text()
    payload = fields.Text()

    def call(self, method, *args, **kwargs):
        """
        partial API to create asynchronous jobs.

        The method will be called later as ``method(*args, **kwargs)`` in a
        new transaction using a copy of the current environment (user, context,
        recordset).  Arguments must be serializable in JSON.

        The job's return value is stored in JSON in the ``payload`` field, and
        web-notification are possible via bus/models/ir_async:IrAsync.call_notify
        """
        recs = getattr(method, '__self__', None)
        if not isinstance(recs, models.BaseModel):
            raise TypeError("You can only create an async task on a recordset.")
        model = recs.__class__
        context = recs.env.context.copy()
        context.pop('async_traceback', '')
        context.pop('async_job_id', '')
        context.pop('default_name', '')
        context.pop('default_notify', '')

        job = self.sudo().create({
            'state': 'created',
            'res_model': model._name,
            'res_ids': json.dumps(recs._ids),
            'method': method.__name__,
            'args': json.dumps(args),
            'kwargs': json.dumps(kwargs),
            'user_id': int(recs.env.uid),
            'context': json.dumps(context),
            'super_user': recs.env.su,

            # on a call from a regular request, this captures the current stack
            # trace; on a call from an async job, this merges the former
            # traceback with the current stack trace.
            'traceback': self._merge_traceback(traceback.format_stack()[:-1]),
        })

        self._cr.postcommit.add(self._notifydb)

        return job

    def call_notify(self, description, method, *args, **kwargs):
        # see bus/models/ir_async:IrAsync.call_notify
        _logger.warning("Web notifications require IM Bus (bus) to be installed")
        return self.with_context(default_name=description).call(method, *args, **kwargs)

    def _notifydb(self):
        """ Notify the workers that a job has been enqueued """
        with odoo.sql_db.db_connect('postgres').cursor() as cr:
            cr.execute('NOTIFY odoo_async, %s', (self.env.cr.dbname,))
        _logger.debug("Async task commited. Workers notified.")

    @classmethod
    def _process_jobs(cls, dbname):
        """ Process all jobs of the selected database """
        db = odoo.sql_db.db_connect(dbname)
        threading.current_thread().dbname = dbname

        # make sure we can process this db
        with db.cursor() as cr:
            query = "SELECT latest_version FROM ir_module_module WHERE name=%s"
            cr.execute(query, ['base'])
            (version,) = cr.fetchone()
            if version is None:
                _logger.warning(
                    "Skipping database %s because of modules to "
                    "install/upgrade/remove.", dbname)
                return
            if version != BASE_VERSION:
                _logger.warning(
                    "Skipping database %s as its base version is not %s.",
                    dbname, BASE_VERSION)
                return

        # process all jobs enqueued in this db
        while True:
            with db.cursor() as manager_cr:

                # acquire job
                manager_cr.execute("""
                    SELECT *
                    FROM ir_async
                    WHERE state = 'created'
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """)
                job = manager_cr.dictfetchone()
                if job is None:
                    break

                # process job
                with api.Environment.manage():
                    with db.cursor() as job_cr:
                        cls._process_job(job_cr, job)

                # update job
                manager_cr.execute("""
                    UPDATE ir_async
                    SET state=%s,
                        payload=%s,
                        write_date=%s
                    WHERE ID = %s""", (
                        job['state'],
                        json.dumps(job['payload']),
                        datetime.datetime.utcnow(),
                        job['id'],
                    ))

    @staticmethod
    def _process_job(job_cr, job):
        """
        Process one job, restore environment and recordset then safely
        call the desired model method.
        """
        for json_field in ('res_ids', 'args', 'kwargs', 'context'):
            job[json_field] = json.loads(job[json_field])

        # The async_job_id is handy for code that need to link an attachment
        # somewhere. The async_traceback is a technical artifact so we can
        # retrieve the complete traceback in case we re-queue an async job.
        job['context']['async_traceback'] = job['traceback']
        job['context']['async_job_id'] = job['id']

        env = api.Environment(job_cr, job['user_id'], job['context'], job['super_user'])
        ir_async = env['ir.async']

        ir_async._pre_process(job)

        try:
            _logger.info('[%d] Calling "%s" on "%s"', job['id'], job['method'], job['res_model'])
            with job_cr.savepoint():
                records = env[job['res_model']].browse(job['res_ids'])
                result = getattr(records, job['method'])(*job['args'], **job['kwargs'])
                json.dumps(result)  # ensure result is serializable
        except Exception as exc:
            job['state'] = 'failed'
            job['payload'] = ir_async._handle_exception(exc, job['id'])
        else:
            if result is None:
                _logger.debug("[%d] Done", job['id'])
                job['state'] = 'done'
            else:
                _logger.debug("[%d] Succeeded, result is %s", job['id'], result)
                job['state'] = 'succeeded'
                job['payload'] = ir_async._json_response(result)

        ir_async._post_process(job)

    def _pre_process(self, job):
        pass

    def _post_process(self, job):
        pass

    def _merge_traceback(self, tb):
        """ Merge the given traceback with all previous levels of execution """
        old_tb = self.env.context.get('async_traceback', '').splitlines(keepends=True)
        if old_tb:
            def fnc_process_job_not_reached(line):
                return not re.search(f'in {self._process_job.__name__}\\W', line)
            old_tb.append("Traceback of async job (most recent call last):\n")
            old_tb.extend(itertools.dropwhile(fnc_process_job_not_reached, tb))
            tb = old_tb
        return "".join(tb)

    def _handle_exception(self, exception, job_id):
        header, *tb = traceback.format_exc().splitlines(keepends=True)
        exc_tb = header + self._merge_traceback(tb)

        if isinstance(exception, odoo.exceptions.UserError):
            _logger.warning("[%d] %s", job_id, exception)
        else:
            _logger.error("[%d] Failed to process async job\n%s", job_id, exc_tb)

        error = {
            'code': 200,
            'message': "Odoo Server Error",
            'data': serialize_exception(exception),
        }
        error['data']['debug'] = exc_tb
        return self._json_response(error=error)

    def _json_response(self, result=None, error=None):
        response = {}
        if result is not None:
            response['result'] = result
        if error is not None:
            response['error'] = error
        return response

    @api.autovacuum
    def _vacuum_terminated_tasks(self):
        self._cr.execute("""
            SELECT id
            FROM ir_async
            WHERE state IN ('failed', 'done')
               OR (state = 'succeeded'
                   AND write_date + interval '3 day' < LOCALTIMESTAMP)
            FOR UPDATE SKIP LOCKED
            """)
        ids = tuple(self._cr.fetchall())
        if ids:
            self._cr.execute("""
                DELETE FROM ir_async
                WHERE id IN %s
                """, (ids,))
        _logger.info("Vacuumed %d terminated asynchronous tasks", len(ids))

    def complete(self):
        self._cr.execute("""
            UPDATE ir_async
            SET state='done',
                write_date=%s
            WHERE id IN %s
              AND user_id = %s
            RETURNING id
            """, (
                datetime.datetime.utcnow(),
                tuple(self.ids),
                self.env.uid,
            ))
        invalid_ids = set(self.ids) - {row[0] for row in self._cr.fetchall()}
        if invalid_ids:
            raise ValueError("The following jobs couldn't be completed: %s", invalid_ids)
