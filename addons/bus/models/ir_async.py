# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class IrAsync(models.Model):
    _inherit = "ir.async"

    notify = fields.Boolean(default=False)

    def call_notify(self, description, method, *args, **kwargs):
        """
        partial-like API to create asynchronous jobs with web notification.

        The method will be called later as ``target(*args, **kwargs)`` in a
        new transaction using a copy of the current environment (user, context,
        recordset). Arguments must be serializable in JSON.

        The notifications are sent via the longpolling bus, they are:

        - created, the task has been enqueued
        - processing, the worker begins to process the task
        - succeeded, the task succeeded with a result the user must process
        - failed, when the task failed with an error
        - done, the task succeeded without result or the user processed it

        See the ``async_job`` javascript service.

        The ``description`` is used to list the task in the systray menu
        in the frontend. You may pass a falsy value to hide the task
        from the systray but still get notified.
        """
        job = self.with_context(
            default_name=description, default_notify=True
        ).call(method, *args, **kwargs)

        # Notify the user a task has been created
        channel = (self._cr.dbname, 'res.partner', self.env.user.partner_id.id)
        self.env['bus.bus'].sendone(channel, {
            'type': 'ir.async',
            'id': job.id,
            'name': job.name,
            'state': job.state,
        })

        return job

    def _pre_process(self, job):
        # Notify the user a task is processing
        super()._pre_process(job)
        if job['notify']:
            channel = (self._cr.dbname, 'res.partner', self.env.user.partner_id.id)
            self.env['bus.bus'].sendone(channel, {
                'type': 'ir.async',
                'id': job['id'],
                'name': job['name'],
                'state': 'processing',
            })
            self._cr.commit()

    def _post_process(self, job):
        # Notify the user a task is completed on the server side
        super()._post_process(job)
        if job['notify']:
            channel = (self._cr.dbname, 'res.partner', self.env.user.partner_id.id)
            self.env['bus.bus'].sendone(channel, {
                'type': 'ir.async',
                'id': job['id'],
                'name': job['name'],
                'state': job['state'],
                'payload': job['payload'],
            })

    def complete(self):
        # Notify all the tabs a task in SUCCEEDED state has been completed by
        # one of the tab.
        super().complete()
        for job in self:
            channel = (self._cr.dbname, 'res.partner', self.env.user.partner_id.id)
            self.env['bus.bus'].sendone(channel, {
                'type': 'ir.async',
                'id': job.id,
                'name': job.name,
                'state': 'done',
            })
