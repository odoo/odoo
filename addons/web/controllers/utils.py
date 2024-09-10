# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import logging

import babel.messages.pofile
import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from werkzeug.urls import iri_to_uri

from odoo.tools.translate import JAVASCRIPT_TRANSLATION_COMMENT
from odoo.tools.misc import file_open
from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


def clean_action(action, env):
    action_type = action.setdefault('type', 'ir.actions.act_window_close')
    if action_type == 'ir.actions.act_window' and not action.get('views'):
        generate_views(action)

    # When returning an action, keep only relevant fields/properties
    readable_fields = env[action['type']]._get_readable_fields()
    action_type_fields = env[action['type']]._fields.keys()

    cleaned_action = {
        field: value
        for field, value in action.items()
        # keep allowed fields and custom properties fields
        if field in readable_fields or field not in action_type_fields
    }

    # Warn about custom properties fields, because use is discouraged
    action_name = action.get('name') or action
    custom_properties = action.keys() - readable_fields - action_type_fields
    if custom_properties:
        _logger.warning("Action %r contains custom properties %s. Passing them "
            "via the `params` or `context` properties is recommended instead",
            action_name, ', '.join(map(repr, custom_properties)))

    return cleaned_action


def ensure_db(redirect='/web/database/selector', db=None):
    # This helper should be used in web client auth="none" routes
    # if those routes needs a db to work with.
    # If the heuristics does not find any database, then the users will be
    # redirected to db selector or any url specified by `redirect` argument.
    # If the db is taken out of a query parameter, it will be checked against
    # `http.db_filter()` in order to ensure it's legit and thus avoid db
    # forgering that could lead to xss attacks.
    if db is None:
        db = request.params.get('db') and request.params.get('db').strip()

    # Ensure db is legit
    if db and db not in http.db_filter([db]):
        db = None

    if db and not request.session.db:
        # User asked a specific database on a new session.
        # That mean the nodb router has been used to find the route
        # Depending on installed module in the database, the rendering of the page
        # may depend on data injected by the database route dispatcher.
        # Thus, we redirect the user to the same page but with the session cookie set.
        # This will force using the database route dispatcher...
        r = request.httprequest
        url_redirect = werkzeug.urls.url_parse(r.base_url)
        if r.query_string:
            # in P3, request.query_string is bytes, the rest is text, can't mix them
            query_string = iri_to_uri(r.query_string.decode())
            url_redirect = url_redirect.replace(query=query_string)
        request.session.db = db
        werkzeug.exceptions.abort(request.redirect(url_redirect.to_url(), 302))

    # if db not provided, use the session one
    if not db and request.session.db and http.db_filter([request.session.db]):
        db = request.session.db

    # if no database provided and no database in session, use monodb
    if not db:
        all_dbs = http.db_list(force=True)
        if len(all_dbs) == 1:
            db = all_dbs[0]

    # if no db can be found til here, send to the database selector
    # the database selector will redirect to database manager if needed
    if not db:
        werkzeug.exceptions.abort(request.redirect(redirect, 303))

    # always switch the session to the computed db
    if db != request.session.db:
        request.session = http.root.session_store.new()
        request.session.update(http.get_default_session(), db=db)
        request.session.context['lang'] = request.default_lang()
        werkzeug.exceptions.abort(request.redirect(request.httprequest.url, 302))


# I think generate_views should go into js ActionManager
def generate_views(action):
    """
    While the server generates a sequence called "views" computing dependencies
    between a bunch of stuff for views coming directly from the database
    (the ``ir.actions.act_window model``), it's also possible for e.g. buttons
    to return custom view dictionaries generated on the fly.

    In that case, there is no ``views`` key available on the action.

    Since the web client relies on ``action['views']``, generate it here from
    ``view_mode`` and ``view_id``.

    Currently handles two different cases:

    * no view_id, multiple view_mode
    * single view_id, single view_mode

    :param dict action: action descriptor dictionary to generate a views key for
    """
    view_id = action.get('view_id') or False
    if isinstance(view_id, (list, tuple)):
        view_id = view_id[0]

    # providing at least one view mode is a requirement, not an option
    view_modes = action['view_mode'].split(',')

    if len(view_modes) > 1:
        if view_id:
            raise ValueError('Non-db action dictionaries should provide '
                             'either multiple view modes or a single view '
                             'mode and an optional view id.\n\n Got view '
                             'modes %r and view id %r for action %r' % (
                view_modes, view_id, action))
        action['views'] = [(False, mode) for mode in view_modes]
        return
    action['views'] = [(view_id, view_modes[0])]


def get_action(env, path_part):
    """
    Get a ir.actions.actions() given an action typically found in a
    "/odoo"-like url.

    The action can take one of the following forms:
    * "action-" followed by a record id
    * "action-" followed by a xmlid
    * "m-" followed by a model name (act_window's res_model)
    * a dotted model name (act_window's res_model)
    * a path (ir.action's path)
    """
    Actions = env['ir.actions.actions']

    if path_part.startswith('action-'):
        someid = path_part.removeprefix('action-')
        if someid.isdigit():  # record id
            action = Actions.sudo().browse(int(someid)).exists()
        elif '.' in someid:   # xml id
            action = env.ref(someid, raise_if_not_found=False)
            if not action or not action._name.startswith('ir.actions'):
                action = Actions
        else:
            action = Actions
    elif path_part.startswith('m-') or '.' in path_part:
        model = path_part.removeprefix('m-')
        if model in env and not env[model]._abstract:
            action = env['ir.actions.act_window'].sudo().search([
                ('res_model', '=', model)], limit=1)
            if not action:
                action = env['ir.actions.act_window'].new(
                    env[model].get_formview_action()
                )
        else:
            action = Actions
    else:
        action = Actions.sudo().search([('path', '=', path_part)])

    if action and action._name == 'ir.actions.actions':
        action_type = action.read(['type'])[0]['type']
        action = env[action_type].browse(action.id)

    return action


def get_action_triples(env, path, *, start_pos=0):
    """
    Extract the triples (active_id, action, record_id) from a "/odoo"-like path.

    >>> env = ...
    >>> list(get_action_triples(env, "/all-tasks/5/project.project/1/tasks"))
    [
        # active_id, action,                     record_id
        ( None,      ir.actions.act_window(...), 5         ), # all-tasks
        ( 5,         ir.actions.act_window(...), 1         ), # project.project
        ( 1,         ir.actions.act_window(...), None      ), # tasks
    ]
    """
    parts = collections.deque(path.strip('/').split('/'))
    active_id = None
    record_id = None

    while parts:
        if not parts:
            e = "expected action at word {} but found nothing"
            raise ValueError(e.format(path.count('/') + start_pos))
        action_name = parts.popleft()
        action = get_action(env, action_name)
        if not action:
            e = f"expected action at word {{}} but found “{action_name}”"
            raise ValueError(e.format(path.count('/') - len(parts) + start_pos))

        record_id = None
        if parts:
            if parts[0] == 'new':
                parts.popleft()
                record_id = None
            elif parts[0].isdigit():
                record_id = int(parts.popleft())

        yield (active_id, action, record_id)

        if len(parts) > 1 and parts[0].isdigit():  # new active id
            active_id = int(parts.popleft())
        elif record_id:
            active_id = record_id


def _get_login_redirect_url(uid, redirect=None):
    """ Decide if user requires a specific post-login redirect, e.g. for 2FA, or if they are
    fully logged and can proceed to the requested URL
    """
    if request.session.uid:  # fully logged
        return redirect or ('/odoo' if is_user_internal(request.session.uid)
                            else '/web/login_successful')

    # partial session (MFA)
    url = request.env(user=uid)['res.users'].browse(uid)._mfa_url()
    if not redirect:
        return url

    parsed = werkzeug.urls.url_parse(url)
    qs = parsed.decode_query()
    qs['redirect'] = redirect
    return parsed.replace(query=werkzeug.urls.url_encode(qs)).to_url()


def is_user_internal(uid):
    return request.env['res.users'].browse(uid)._is_internal()


def _local_web_translations(trans_file):
    messages = []
    try:
        with file_open(trans_file, filter_ext=('.po')) as t_file:
            po = babel.messages.pofile.read_po(t_file)
    except Exception:
        return
    for x in po:
        if x.id and x.string and JAVASCRIPT_TRANSLATION_COMMENT in x.auto_comments:
            messages.append({'id': x.id, 'string': x.string})
    return messages
