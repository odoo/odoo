# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import logging
import re
from collections import defaultdict
from datetime import date
from http import HTTPStatus
from urllib.parse import urlencode

import psycopg2.errors
from dateutil.relativedelta import relativedelta
from lxml import etree
from werkzeug.exceptions import BadRequest, NotFound

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.models import regex_object_name
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

from .utils import get_action_triples

_logger = logging.getLogger(__name__)


class WebJsonController(http.Controller):

    # for /json, the route should work in a browser, therefore type=http
    @http.route('/json/<path:subpath>', auth='user', type='http', readonly=True)
    def web_json(self, subpath, **kwargs):
        self._check_json_route_active()
        return request.redirect(
            f'/json/1/{subpath}?{urlencode(kwargs)}',
            HTTPStatus.TEMPORARY_REDIRECT
        )

    @http.route('/json/1/<path:subpath>', auth='bearer', type='http', readonly=True)
    def web_json_1(self, subpath, **kwargs):
        """Simple JSON representation of the views.

        Get the JSON representation of the action/view as it would be shown
        in the web client for the same /odoo `subpath`.

        Behaviour:
        - When, the action resolves to a pair (Action, id), `form` view_type.
          Otherwise when it resolves to (Action, None), use the given view_type
          or the preferred one.
        - View form uses `web_read`.
        - If a groupby is given, use a read group.
          Views pivot, graph redirect to a canonical URL with a groupby.
        - Otherwise use a search read.
        - If any parameter is missing, redirect to the canonical URL (one where
          all parameters are set).

        :param subpath: Path to the (window) action to execute
        :param view_type: View type from which we generate the parameters
        :param domain: The domain for searches
        :param offset: Offset for search
        :param limit: Limit for search
        :param groupby: Comma-separated string; when set, executes a `web_read_group`
                        and groups by the given fields
        :param fields: Comma-separates aggregates for the "group by" query
        :param start_date: When applicable, minimum date (inclusive bound)
        :param end_date: When applicable, maximum date (exclusive bound)
        """
        self._check_json_route_active()
        if not request.env.user.has_group('base.group_allow_export'):
            raise AccessError(request.env._("You need export permissions to use the /json route"))

        # redirect when the computed kwargs and the kwargs from the URL are different
        param_list = set(kwargs)

        def check_redirect():
            # when parameters were added, redirect
            if set(param_list) == set(kwargs):
                return None
            # for domains, make chars as safe
            encoded_kwargs = urlencode(kwargs, safe="()[], '\"")
            return request.redirect(
                f'/json/1/{subpath}?{encoded_kwargs}',
                HTTPStatus.TEMPORARY_REDIRECT
            )

        # Get the action
        env = request.env
        action, context, eval_context, record_id = self._get_action(subpath)
        model = env[action.res_model].with_context(context)

        # Get the view
        view_type = kwargs.get('view_type')
        if not view_type and record_id:
            view_type = 'form'
        view_id, view_type = get_view_id_and_type(action, view_type)
        view = model.get_view(view_id, view_type)
        spec = model._get_fields_spec(view)

        # Simple case: form view with record
        if view_type == 'form' or record_id:
            if redirect := check_redirect():
                return redirect
            if not record_id:
                raise BadRequest(env._("Missing record id"))
            res = model.browse(int(record_id)).web_read(spec)[0]
            return request.make_json_response(res)

        # Find domain and limits
        domains = [safe_eval(action.domain or '[]', eval_context)]
        if 'domain' in kwargs:
            # for the user-given domain, use only literal-eval instead of safe_eval
            user_domain = ast.literal_eval(kwargs.get('domain') or '[]')
            domains.append(user_domain)
        else:
            default_domain = get_default_domain(model, action, context, eval_context)
            if default_domain and default_domain != expression.TRUE_DOMAIN:
                kwargs['domain'] = repr(default_domain)
            domains.append(default_domain)
        try:
            limit = int(kwargs.get('limit', 0)) or action.limit
            offset = int(kwargs.get('offset', 0))
        except ValueError as exc:
            raise BadRequest(exc.args[0]) from exc
        if 'offset' not in kwargs:
            kwargs['offset'] = offset
        if 'limit' not in kwargs:
            kwargs['limit'] = limit

        # Additional info from the view
        view_tree = etree.fromstring(view['arch'])

        # Add date domain for some view types
        if view_type in ('calendar', 'gantt', 'cohort'):
            try:
                start_date = date.fromisoformat(kwargs['start_date'])
                end_date = date.fromisoformat(kwargs['end_date'])
            except ValueError as exc:
                raise BadRequest(exc.args[0]) from exc
            except KeyError:
                start_date = end_date = None
            date_domain = get_date_domain(start_date, end_date, view_tree)
            domains.append(date_domain)
            if 'start_date' not in kwargs or end_date not in kwargs:
                kwargs.update({
                    'start_date': date_domain[0][2].isoformat(),
                    'end_date': date_domain[1][2].isoformat(),
                })

        # Add explicitly activity fields for an activity view
        if view_type == 'activity':
            domains.append([('activity_ids', '!=', False)])
            # add activity fields
            for field_name, field in model._fields.items():
                if field_name.startswith('activity_') and field_name not in spec and field.is_accessible(env):
                    spec[field_name] = {}

        # Group by
        groupby, fields = get_groupby(view_tree, kwargs.get('groupby'), kwargs.get('fields'))
        if groupby is not None and not kwargs.get('groupby'):
            # add arguments to kwargs
            kwargs['groupby'] = ','.join(groupby)
            if 'fields' not in kwargs and fields:
                kwargs['fields'] = ','.join(fields)
        if groupby is None and fields:
            # add fields to the spec
            for field in fields:
                spec.setdefault(field, {})

        # Last checks before the query
        if redirect := check_redirect():
            return redirect
        domain = expression.AND(domains)
        # Reading a group or a list
        if groupby:
            res = model.web_read_group(
                domain,
                fields=fields or ['__count'],
                groupby=groupby,
                limit=limit,
                lazy=False,
            )
            # pop '__domain' key
            for value in res['groups']:
                del value['__domain']
        else:
            res = model.web_search_read(
                domain,
                spec,
                limit=limit,
                offset=offset,
            )
        return request.make_json_response(res)

    def _check_json_route_active(self):
        # experimental route, only enabled in demo mode or when explicitly set
        if not (request.env.ref('base.module_base').demo
                or request.env['ir.config_parameter'].sudo().get_param('web.json.enabled')):
            raise NotFound()

    def _get_action(self, subpath):
        def get_action_triples_():
            try:
                yield from get_action_triples(request.env, subpath, start_pos=1)
            except ValueError as exc:
                raise BadRequest(exc.args[0]) from exc

        context = dict(request.env.context)
        active_id, action, record_id = list(get_action_triples_())[-1]
        action = action.sudo()
        if action.usage == 'ir_actions_server' and action.path:
            # force read-only evaluation of action_data
            try:
                with action.pool.cursor(readonly=True) as ro_cr:
                    if not ro_cr.readonly:
                        ro_cr.connection.set_session(readonly=True)
                    assert ro_cr.readonly
                    action_data = action.with_env(action.env(cr=ro_cr, su=False)).run()
            except psycopg2.errors.ReadOnlySqlTransaction as e:
                # never retry on RO connection, just leave
                raise AccessError(action.env._("Unsupported server action")) from e
            except ValueError as e:
                # safe_eval wraps the error into a ValueError (as str)
                if "ReadOnlySqlTransaction" not in e.args[0]:
                    raise
                raise AccessError(action.env._("Unsupported server action")) from e
            # transform data into a new record
            action = action.env[action_data['type']]
            action = action.new(action_data, origin=action.browse(action_data.pop('id')))
        if action._name != 'ir.actions.act_window':
            e = f"{action._name} are not supported server-side"
            raise BadRequest(e)
        eval_context = dict(
            action._get_eval_context(action),
            active_id=active_id,
            context=context,
            allowed_company_ids=request.env.user.company_ids.ids,
        )
        # update the context and return
        context.update(safe_eval(action.context, eval_context))
        return action, context, eval_context, record_id


def get_view_id_and_type(action, view_type: str | None) -> tuple[int | None, str]:
    """Extract the view id from the action"""
    assert action._name == 'ir.actions.act_window'
    view_modes = action.view_mode.split(',')
    if not view_type:
        view_type = view_modes[0]
    for view_id, action_view_type in action.views:
        if view_type == action_view_type:
            break
    else:
        if view_type not in view_modes:
            raise BadRequest(request.env._(
                "Invalid view type '%(view_type)s' for action id=%(action)s",
                view_type=view_type,
                action=action.id,
            ))
        view_id = False
    return view_id, view_type


def get_default_domain(model, action, context, eval_context):
    for ir_filter in model.env['ir.filters'].get_filters(model._name, action._origin.id):
        if ir_filter['is_default']:
            # user filters, static parsing only
            domain_str = ir_filter['domain']
            domain_str = re.sub(r'\buid\b', str(model.env.uid), domain_str)
            default_domain = ast.literal_eval(domain_str)
            break
    else:
        def filters_from_context():
            view_tree = None
            for key, value in context.items():
                if key.startswith('search_default_') and value:
                    filter_name = key[15:]
                    if not regex_object_name.match(filter_name):
                        raise ValueError(model.env._("Invalid default search filter name for %s", key))
                    if view_tree is None:
                        view = model.get_view(action.search_view_id.id, 'search')
                        view_tree = etree.fromstring(view['arch'])
                    if (element := view_tree.find(Rf'.//filter[@name="{filter_name}"]')) is not None:
                        # parse the domain
                        if domain := element.attrib.get('domain'):
                            yield domain
                        # not parsing context['group_by']

        default_domain = expression.AND(
            safe_eval(domain, eval_context)
            for domain in filters_from_context()
        )
    return default_domain


def get_date_domain(start_date, end_date, view_tree):
    if not start_date or not end_date:
        start_date = date.today() + relativedelta(day=1)
        end_date = start_date + relativedelta(months=1)
    date_field = view_tree.attrib.get('date_start')
    if not date_field:
        raise ValueError("Could not find the date field in the view")
    return [(date_field, '>=', start_date), (date_field, '<', end_date)]


def get_groupby(view_tree, groupby=None, fields=None):
    """Parse the given groupby and fields and fallback to the view if not provided.

    Return the groupby as a list when given.
    Otherwise find groupby and fields from the view.

    :param view_tree: The xml tree of the view
    :param groupby: string or None
    :param fields: string or None
    """
    if groupby:
        groupby = groupby.split(',')
    if fields:
        fields = fields.split(',')
    else:
        fields = None
    if groupby is not None:
        return groupby, fields

    if view_tree.tag in ('pivot', 'graph'):
        # extract groupby from the view if we don't have any
        field_by_type = defaultdict(list)
        for element in view_tree.findall(r'./field'):
            field_name = element.attrib.get('name')
            if element.attrib.get('invisible', '') in ('1', 'true'):
                field_by_type['invisible'].append(field_name)
            else:
                field_by_type[element.attrib.get('type', 'normal')].append(field_name)
            # not reading interval from the attribute
        groupby = [
            *field_by_type.get('row', ()),
            *field_by_type.get('col', ()),
            *field_by_type.get('normal', ()),
        ]
        if fields is None:
            fields = field_by_type.get('measure', [])
        return groupby, fields
    if view_tree.attrib.get('default_group_by'):
        # in case the kanban view (or other) defines a default grouping
        # return the field name so it is added to the spec
        field = view_tree.attrib.get('default_group_by')
        return (None, [field] if field else [])
    return None, None
