# -*- coding: utf-8 -*-
import datetime
import logging

from odoo import fields, models, api


_logger = logging.getLogger(__name__)


class CvIrCronHistory(models.Model):
    _name = 'cv.ir.cron.history'
    _description = 'Cron History'
    _rec_name = 'ir_cron_id'
    _order = 'id desc'

    ir_cron_id = fields.Many2one('ir.cron', string='Cron', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)
    type = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], string='Type', readonly=True)
    state = fields.Selection([('success', 'Success'), ('fail', 'Failed'), ('interruption', 'Interruption'), ('running', 'Running')],
                             string='State', readonly=True, default='running',
                             help="  * Success: The cron finished successfully.\n"
                                  "  * Failed: The cron finished with an error.\n"
                                  "  * Interruption: The cron was interrupted (server restart, ...).\n"
                                  "  * Running: The cron is currently running.")

    started_at = fields.Datetime(string='Started At', readonly=True, default=fields.Datetime.now)
    ended_at = fields.Datetime(string='Ended At', readonly=True)
    duration = fields.Float(string='Duration', readonly=True, group_operator="avg", help='Duration in seconds')

    error = fields.Text(string='Error', readonly=True, help='Error message if the cron failed.')

    def _register_hook(self):
        """ Register a hook to automatically set the state to interruption when the server is restarted. """
        history = self.env['cv.ir.cron.history'].sudo().search([('state', '=', 'running')])
        history.write({'state': 'interruption'})
        if history:
            _logger.info('Cron History: %s cron(s) interrupted', len(history))

    def finish(self, success, error=False):
        self.ensure_one()
        update = {
            'state': 'success' if success else 'fail',
            'ended_at': fields.Datetime.now(),
            'duration': (fields.Datetime.now() - self.started_at).total_seconds() / 60,
        }
        if error:
            update['error'] = error
        self.write(update)

    def name_get(self):
        return [(cron.id, '{}'.format(cron.ir_cron_id.name)) for cron in self]

    @api.autovacuum
    def _gc_history(self):
        # delete history older than 30 days
        domain = [('create_date', '<', fields.Datetime.now() - datetime.timedelta(days=30))]
        return self.sudo().search(domain).unlink()
