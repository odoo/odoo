import logging
import requests
import threading

from odoo import api, models, fields, _
from datetime import datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class IrWebhook(models.Model):
    _name = "ir.webhook"
    _description = "Webhook Excution"
    _max_rety_attempt = 5

    url = fields.Char()
    data = fields.Json()
    retry_attempt = fields.Integer()
    executed_at = fields.Datetime()
    state = fields.Selection(selection=[('scheduled', 'Scheduled'), ('done', 'Done'), ('error', 'Error')], default="scheduled")
    msg = fields.Char(default="")

    @api.autovacuum
    def _gc_cron_triggers(self):
        domain = [('state', 'in', ['done', 'error']), ('create_date', '<', datetime.now() + relativedelta(months=-1))]
        records = self.search(domain, limit=models.GC_UNLINK_LIMIT)
        if len(records) >= models.GC_UNLINK_LIMIT:
            self.env.ref('base.autovacuum_job')._trigger()
        return records.unlink()

    def _get_domain_webhook_execute(self):
        return [('state', '=', 'scheduled')]

    def _append_message(self, msg):
        self.ensure_one()
        if self.msg:
            return self.msg + "\n" + msg
        else:
            return msg

    @api.model
    def _cron_execute_webhook(self, limit=100, api_timeout=1):
        """ Execute the Webhook Post"""
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        webhooks = self.sudo().search(self._get_domain_webhook_execute(), limit=limit)
        webhook_done = 0
        retrigger_cron = len(webhooks) >= limit
        for webhook_call in webhooks:
            if webhook_call.retry_attempt >= self._max_rety_attempt:
                webhook_call.write({'state': "error", 'msg': webhook_call._append_message(_("Reach maximum retry - %s", self._max_rety_attempt))})
                continue

            try:
                # 'send and forget' strategy, and avoid locking the user if the webhook
                # is slow or non-functional (we still allow for a 1s timeout so that
                # if we get a proper error response code like 400, 404 or 500 we can log)
                response = requests.post(webhook_call.url, data=webhook_call.data, headers={'Content-Type': 'application/json'}, timeout=api_timeout)
                response.raise_for_status()
            except requests.exceptions.ReadTimeout:
                _logger.warning("Webhook call timed out after %ss - it may or may not have failed. "
                                "If this happens often, it may be a sign that the system you're "
                                "trying to reach is slow or non-functional.", api_timeout)
                webhook_call.write({"retry_attempt": webhook_call.retry_attempt + 1, 'msg': webhook_call._append_message(_("Webhook call timed out after - %ss", api_timeout))})
                retrigger_cron = True
            except requests.exceptions.RequestException as e:
                _logger.warning("Webhook call failed: %s", e)
                webhook_call.write({"state": 'error', 'msg': webhook_call._append_message(_("Webhook call failed: %s", e))})
            except Exception as e:  # noqa: BLE001
                webhook_call.write({"state": 'error', 'msg': webhook_call._append_message(_("Wow, your webhook call failed with a really unusual error: %s", e))})
            else:
                webhook_call.write({"state": "done", "executed_at": self.env.cr.now()})
            finally:
                webhook_done += 1

            if auto_commit:
                self.env['ir.cron']._notify_progress(done=webhook_done, remaining=len(webhooks) - webhook_done)
                self.env.cr.commit()

        self.env['ir.cron']._notify_progress(done=webhook_done, remaining=len(webhooks) - webhook_done)

        if retrigger_cron:
            self.env.ref('base.execute_webhook')._trigger()
