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
    @http.route('/json/<path:subpath>', auth='bearer', type='http', readonly=True)
    def web_json(self, subpath, **kwargs):
        return request.redirect(
            f'/json/18.0/{subpath}?{urlencode(kwargs)}',
            HTTPStatus.TEMPORARY_REDIRECT
        )

    @http.route('/json/18.0/<path:subpath>', auth='bearer', type='http', readonly=True)
    def web_json_18_0(self, subpath, view_type=None, limit=0, offset=0):
        if not request.env.user.has_group('base.group_allow_export'):
            raise AccessError(_("You need export permissions to use the /json route"))

        try:
            limit = int(limit)
            offset = int(offset)
        except ValueError as exc:
            raise BadRequest(exc.args[0])
        context = dict(request.env.context)

        def get_action_triples_():
            try:
                yield from get_action_triples(request.env, subpath, start_pos=1)
            except ValueError as exc:
                raise BadRequest(exc.args[0])

        # Hack for OXP. We are not sure yet if we wanna run all server
        # actions, but we are sure we want to run those ones. TODO: find
        # a better way to do it.
        allowed_server_action_paths = {'crm'}

        for active_id, action, record_id in get_action_triples_():
            if action.sudo().path in allowed_server_action_paths:
                try:
                    action = request.env['ir.actions.act_window'].new(
                        action.sudo(False).run())
                except psycopg2.errors.ReadOnlySqlTransaction as e:
                    # never retry on RO connection, just leave
                    raise AccessError() from e
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

        model = request.env[action.res_model].with_context(context)
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
