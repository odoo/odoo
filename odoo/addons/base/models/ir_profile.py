import json
import base64
import datetime

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.profiler import SpeedscopeResult


class IrProfileSession(models.Model):
    _name = 'ir.profile.session'
    _description = 'Ir profile sessions'
    _order = 'id desc'

    name = fields.Char('Name')
    execution_ids = fields.One2many('ir.profile.execution', 'profile_session_id')

    def _action_generate_speedscope(self):
        return self.execution_ids._action_generate_speedscope()

    @api.autovacuum
    def _gc_session(self):
        domain = [('create_date', '<', fields.Datetime.now() - datetime.timedelta(days=30))]
        return self.sudo().search(domain).unlink()

    def _profiling_enabled(self):
        return request.env['ir.config_parameter'].sudo().get_param('base.profiling_enabled') # change to duration?

    def _update_profiling(self, profile=None, profile_sql=None, profile_traces_sync=None, profile_traces_async=None, **_kwargs):
        if profile:
            if self._profiling_enabled():
                if not request.session.profile_session_id:
                    request.session.profile_session_id = self.create({'name': self.env.user.name}).id
            else:
                raise UserError('Profiling is not enabled on this database')
        elif profile is False:
            request.session.profile_session_id = False

        def check(flag_set, flag, value):
            if value is True:
                flag_set.add(flag)
            elif value is False:
                flag_set.discard(flag)
        profile_modes = set(request.session.profile_modes or [])
        check(profile_modes, 'profile_sql', profile_sql)
        check(profile_modes, 'profile_traces_sync', profile_traces_sync)
        check(profile_modes, 'profile_traces_async', profile_traces_async)
        request.session.profile_modes = list(profile_modes)
        return {
            'profile_session_id': request.session.profile_session_id,
            'profile_modes': request.session.profile_modes,
        }


class IrProfileExcecution(models.Model):
    _name = 'ir.profile.execution'
    _description = 'Ir profile execution'

    description = fields.Char('Description')
    profile_session_id = fields.Many2one('ir.profile.session', ondelete='cascade')
    duration = fields.Float('Duration')

    # results slots

    init_stack_trace = fields.Char('init_stack_trace', prefetch=False)

    sql = fields.Char('Sql', prefetch=False)
    traces_async = fields.Char('Traces Async', prefetch=False)
    traces_sync = fields.Char('Traces Sync', prefetch=False)

    speedscope = fields.Binary('Speedscope', prefetch=False)  # this binary field is painfull
    speedscope_url = fields.Char('Open', compute='_compute_url')

    def _compute_url(self):
        url_root = request.httprequest.url_root
        for profile in self:
            if profile.speedscope:
                content_url = '%sweb/content/ir.profile.execution/%s/speedscope' % (url_root, profile.id)
                profile.speedscope_url = '/base/static/lib/speedscope/index.html#profileURL=%s' % content_url
            else:
                profile.speedscope_url = ''

    def _action_generate_speedscope(self):
        for execution in self:
            trace_result = None
            sql_result = None
            #if profile.speedscope:
            #    continue
            results = {}
            if execution.sql:
                results['sql'] = json.loads(execution.sql)
            if execution.traces_async:
                results['frames'] = json.loads(execution.traces_async)
            if execution.traces_sync:
                results['settrace'] = json.loads(execution.traces_sync)

            sp = SpeedscopeResult(init_stack_trace=json.loads(execution.init_stack_trace), **results)
            if 'sql' in results:
                sp.add_profile(['sql'], hide_gaps=True, display_name='sql (no gap)')
                sp.add_profile(['sql'], continuous=False, display_name='sql queries') # todo remove this continuous param
            if 'frames' in results:
                sp.add_profile(['frames'], display_name='Profile frames')
            if 'settrace' in results:
                sp.add_profile(['settrace'], display_name='Settrace frames')
            if len(results.keys()) > 1:
                sp.add_profile(results.keys(), display_name='Combined')
            result = sp.make()
            execution.speedscope = base64.b64encode(json.dumps(result).encode('utf-8'))
