# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import base64
import datetime

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.profiler import make_session
from odoo.tools.speedscope import Speedscope


class IrProfile(models.Model):
    _name = 'ir.profile'
    _description = 'Profiling results'
    _log_access = False  # avoid useless foreign key on res_user
    _order = 'session desc, id desc'

    create_date = fields.Datetime('Creation Date')

    session = fields.Char('Session', index=True)
    name = fields.Char('Description')
    duration = fields.Float('Duration')

    init_stack_trace = fields.Text('Initial stack trace', prefetch=False)

    sql = fields.Text('Sql', prefetch=False)
    traces_async = fields.Text('Traces Async', prefetch=False)
    traces_sync = fields.Text('Traces Sync', prefetch=False)

    speedscope = fields.Binary('Speedscope', compute='_compute_speedscope')

    @api.autovacuum
    def _gc_profile(self):
        # remove profiles older than 30 days
        domain = [('create_date', '<', fields.Datetime.now() - datetime.timedelta(days=30))]
        return self.sudo().search(domain).unlink()

    def _compute_speedscope(self):
        for execution in self:
            sp = Speedscope(init_stack_trace=json.loads(execution.init_stack_trace))
            if execution.sql:
                sp.add('sql', json.loads(execution.sql))
            if execution.traces_async:
                sp.add('frames', json.loads(execution.traces_async))
            if execution.traces_sync:
                sp.add('settrace', json.loads(execution.traces_sync))

            result = json.dumps(sp.add_default().make())
            execution.speedscope = base64.b64encode(result.encode('utf-8'))
