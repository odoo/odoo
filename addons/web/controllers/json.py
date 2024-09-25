# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from http import HTTPStatus
from urllib.parse import urlencode

import psycopg2.errors
from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import _

from .utils import get_action_triples

_logger = logging.getLogger(__name__)


class WebJsonController(http.Controller):

    # for /json, the route should work in a browser, therefore type=http
    @http.route('/json/<path:subpath>', auth='user', type='http', readonly=True)
    def web_json(self, subpath, **kwargs):
        return request.redirect(
            f'/json/1/{subpath}?{urlencode(kwargs)}',
            HTTPStatus.TEMPORARY_REDIRECT
        )

    @http.route('/json/1/<path:subpath>', auth='bearer', type='http', readonly=True)
    def web_json_1(self, subpath, view_type=None, limit=0, offset=0):
        """Simple JSON representation of the views.

        Behaviour:
        - we have a `record_id` (form view) and we `web_read` the spec
        - otherwise `web_search_read`

        :param subpath: Path to the (window) action to execute
        :param view_type: View type from which we generate the parameters
        :param offset: Offset for search
        :param limit: Limit for search
        """
        env = request.env
        if not env.user.has_group('base.group_allow_export'):
            raise AccessError(_("You need export permissions to use the /json route"))

        try:
            limit = int(limit)
            offset = int(offset)
        except ValueError as exc:
            raise BadRequest(exc.args[0])
        context = dict(env.context)

        def get_action_triples_():
            try:
                yield from get_action_triples(env, subpath, start_pos=1)
            except ValueError as exc:
                raise BadRequest(exc.args[0])

        for active_id, action, record_id in get_action_triples_():
            action_sudo = action.sudo()
            if action_sudo.usage == 'ir_actions_server' and action_sudo.path:
                try:
                    with action.pool.cursor(readonly=True) as ro_cr:
                        if not ro_cr.readonly:
                            ro_cr.connection.set_session(readonly=True)
                        assert ro_cr.readonly
                        action_data = action.with_env(action.env(cr=ro_cr)).run()
                except psycopg2.errors.ReadOnlySqlTransaction as e:
                    # never retry on RO connection, just leave
                    raise AccessError(env._("Read-only action allowed")) from e
                except ValueError as e:
                    # safe_eval wraps the error into a ValueError (as str)
                    if "ReadOnlySqlTransaction" in e.args[0]:
                        raise AccessError(env._("Read-only action allowed")) from e
                    raise
                # transform data into a new record
                action = env[action_data['type']]
                action = action.new(action_data, origin=action.browse(action_data.pop('id')))
            if action._name != 'ir.actions.act_window':
                e = f"{action._name} are not supported server-side"
                raise BadRequest(e)
            context.update(safe_eval(action.context, dict(
                action._get_eval_context(action),
                active_id=active_id,
                context=context,
            )))

        if not view_type:
            if record_id:
                view_type = 'form'
            else:
                view_type = action.view_mode.split(',')[0]

        model = env[action.res_model].with_context(context)
        view = model.get_view(view_type=view_type)
        spec = model._get_fields_spec(view)

        if record_id:
            res = model.browse(int(record_id)).web_read(spec)[0]
        else:
            domain = safe_eval(action.domain or '[]', dict(
                action._get_eval_context(action),
                context=context,
                active_id=active_id,
                allowed_company_ids=[1],
            ))
            res = model.web_search_read(
                domain,
                spec,
                limit=limit or action.limit,
                offset=offset,
            )

        return request.make_json_response(res)
