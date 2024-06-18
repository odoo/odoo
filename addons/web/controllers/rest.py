import collections
import logging
from http import HTTPStatus

from werkzeug.exceptions import BadRequest, HTTPException

from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import (
    Controller,
    HttpDispatcher,
    SessionExpiredException,
    request,
    route,
)
from odoo.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)


def get_action(env, action_path):
    """
    Find the ir.actions.actions() record given its path. It returns an
    empty ir.actions.actions() record when not found.

    The following path patterns are supported:
    * "action-" followed by a record id
    * "action-" followed by a xmlid
    * "m-" followed by a model name (act_window, res_model field)
    * a dotted model name (act_window, res_model field)
    * a path (any action's path field)
    """
    Actions = env['ir.actions.actions']

    if action_path.startswith('action-'):
        someid = action_path.removeprefix('action-')
        if someid.isdigit():  # record id
            action = Actions.sudo().browse(int(someid)).exists()
        elif '.' in someid:   # xml id
            action = env.ref(someid, False)
            if not action or not action._name.startswith('ir.actions'):
                action = Actions
        else:
            action = Actions
    elif action_path.startswith('m-') or '.' in action_path:
        model = action_path.removeprefix('m-')
        if model in env:
            action = env['ir.actions.act_window'].sudo().search([
                ('res_model', '=', model)], limit=1)
        else:
            action = Actions
    else:
        action = Actions.sudo().search([('path', '=', action_path)])

    if action:
        action_type = action.read(['type'])[0]['type']
        action = env[action_type].browse(action.id)

    return action

def extract_actions(env, path):
    """
    Extract the triples (active_id, action, record_id) from a "/odoo"-like path.

    >>> env = ...
    >>> list(extract_actions(env, "/all-tasks/5/project.project/1/tasks"))
    [
        # active_id, action,                     record_id
        ( None,      ir.actions.act_window(...), 5         ), # all-tasks
        ( 5,         ir.actions.act_window(...), 1         ), # project.project
        ( 1,         ir.actions.act_window(...), None      ), # tasks
    ]
    """
    words = collections.deque(path.strip('/').split('/'))
    active_id = None

    while words:
        if words[0].isdigit():  # new active id
            active_id = int(words.popleft())

        if not words:
            e = "expected action at word {} but found nothing"
            raise ValueError(e.format(path.count('/')))
        action_name = words.popleft()
        action = get_action(env, action_name)
        if not action:
            e = f"expected action at place {{}} but found “{action_name}”"
            raise ValueError(e.format(path.count('/') - len(words)))

        record_id = None
        if words:
            if words[0] == 'new':
                words.popleft()
            elif words[0].isdigit():
                active_id = record_id = int(words.popleft())

        yield (active_id, action, record_id)


class RestDispatcher(HttpDispatcher):
    routing_type = 'rest'

    @classmethod
    def is_compatible_with(cls, request):
        return request.httprequest.mimetype in ('', 'application/json')

    def _get_params(self, args):
        try:
            return dict(self.request.get_json_params(), **args)
        except ValueError as exc:
            raise BadRequest(f"{type(exc).__name__}: {exc}")

    def handle_error(self, exc):
        if isinstance(exc, HTTPException):
            code = exc.code
            msg = exc.get_description()
        if isinstance(exc, SessionExpiredException):
            code = HTTPStatus.FORBIDDEN
            msg = "session expired"
        elif isinstance(exc, (AccessDenied, AccessError)):
            code = HTTPStatus.FORBIDDEN
            msg = exc.args[0]
        elif isinstance(exc, UserError):
            code = HTTPStatus.BAD_REQUEST
            msg = exc.args[0]
        else:
            code = HTTPStatus.INTERNAL_SERVER_ERROR
            msg = code.description
        return request.make_json_response(msg, status=code)


class Rest(Controller):
    @route('/json/<path:pathname>', auth='public', type='rest', methods=['GET'])
    def web_json_get(self, pathname, view_type=None, limit=0, offset=0):
        context = dict(request.env.context)

        for active_id, action, record_id in extract_actions(request.env, pathname):
            if action._name != 'ir.actions.act_window':
                e = f"{action._name} are not supported server-side"
                raise BadRequest(e)
            context.update(safe_eval(action.context, dict(
                action._get_eval_context(action),
                active_id=active_id,
                context=context,
            )))

        model = request.env[action.res_model].with_context(context)

        view = model.get_view(view_type=view_type or (
            'form' if record_id else action.view_mode.split(',')[0]
        ))
        spec = request.env['ir.ui.view']._get_fields_spec(view)

        if record_id:
            res = model.browse(int(record_id)).web_read(spec)[0]
        else:
            domain = safe_eval(action.domain or '[]', dict(
                action._get_eval_context(action),
                context=context,
                active_id=active_id,
            ))
            res = model.search(
                domain,
                limit=int(limit) or action.limit,
                offset=int(offset),
            ).web_read(spec)

        return request.make_json_response(res)
