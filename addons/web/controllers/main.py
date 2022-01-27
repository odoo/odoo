# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import copy
import datetime
import functools
import hashlib
import io
import itertools
import json
import logging
import operator
import os
import re
import sys
import tempfile
import unicodedata
from collections import OrderedDict, defaultdict

import babel.messages.pofile
import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from lxml import etree, html
from markupsafe import Markup
from werkzeug.urls import url_encode, url_decode, iri_to_uri

import odoo
import odoo.modules.registry
from odoo.api import call_kw
from odoo.addons.base.models.ir_qweb import render as qweb_render
from odoo.modules import get_resource_path, module
from odoo.tools import html_escape, pycompat, ustr, apply_inheritance_specs, lazy_property, float_repr, osutil
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.translate import _
from odoo.tools.misc import str2bool, xlsxwriter, file_open, file_path
from odoo.tools.safe_eval import safe_eval, time
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.models import check_method_name
from odoo.service import db, security

_logger = logging.getLogger(__name__)

CONTENT_MAXAGE = http.STATIC_CACHE_LONG  # menus, translations, static qweb

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

COMMENT_PATTERN = r'Modified by [\s\w\-.]+ from [\s\w\-.]+'

def none_values_filtered(func):
    @functools.wraps(func)
    def wrap(iterable):
        return func(v for v in iterable if v is not None)
    return wrap

def allow_empty_iterable(func):
    """
    Some functions do not accept empty iterables (e.g. max, min with no default value)
    This returns the function `func` such that it returns None if the iterable
    is empty instead of raising a ValueError.
    """
    @functools.wraps(func)
    def wrap(iterable):
        iterator = iter(iterable)
        try:
            value = next(iterator)
            return func(itertools.chain([value], iterator))
        except StopIteration:
            return None
    return wrap

OPERATOR_MAPPING = {
    'max': none_values_filtered(allow_empty_iterable(max)),
    'min': none_values_filtered(allow_empty_iterable(min)),
    'sum': sum,
    'bool_and': all,
    'bool_or': any,
}

#----------------------------------------------------------
# Odoo Web helpers
#----------------------------------------------------------

db_list = http.db_list

db_monodb = http.db_monodb

def clean(name): return name.replace('\x3c', '')
def serialize_exception(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            _logger.exception("An exception occurred during an http request")
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return werkzeug.exceptions.InternalServerError(json.dumps(error))
    return wrap

def abort_and_redirect(url):
    response = request.redirect(url, 302)
    response = http.root.get_response(request.httprequest, response, explicit_session=False)
    werkzeug.exceptions.abort(response)

def ensure_db(redirect='/web/database/selector'):
    # This helper should be used in web client auth="none" routes
    # if those routes needs a db to work with.
    # If the heuristics does not find any database, then the users will be
    # redirected to db selector or any url specified by `redirect` argument.
    # If the db is taken out of a query parameter, it will be checked against
    # `http.db_filter()` in order to ensure it's legit and thus avoid db
    # forgering that could lead to xss attacks.
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
            query_string = iri_to_uri(r.query_string)
            url_redirect = url_redirect.replace(query=query_string)
        request.session.db = db
        abort_and_redirect(url_redirect.to_url())

    # if db not provided, use the session one
    if not db and request.session.db and http.db_filter([request.session.db]):
        db = request.session.db

    # if no database provided and no database in session, use monodb
    if not db:
        db = db_monodb(request.httprequest)

    # if no db can be found til here, send to the database selector
    # the database selector will redirect to database manager if needed
    if not db:
        werkzeug.exceptions.abort(request.redirect(redirect, 303))

    # always switch the session to the computed db
    if db != request.session.db:
        request.session.logout()
        abort_and_redirect(request.httprequest.url)

    request.session.db = db

def fs2web(path):
    """convert FS path into web path"""
    return '/'.join(path.split(os.path.sep))

def get_last_modified(files):
    """ Returns the modification time of the most recently modified
    file provided

    :param list(str) files: names of files to check
    :return: most recent modification time amongst the fileset
    :rtype: datetime.datetime
    """
    files = list(files)
    if files:
        return max(datetime.datetime.fromtimestamp(os.path.getmtime(f))
                   for f in files)
    return datetime.datetime(1970, 1, 1)

def make_conditional(response, last_modified=None, etag=None, max_age=0):
    """ Makes the provided response conditional based upon the request,
    and mandates revalidation from clients

    Uses Werkzeug's own :meth:`ETagResponseMixin.make_conditional`, after
    setting ``last_modified`` and ``etag`` correctly on the response object

    :param response: Werkzeug response
    :type response: werkzeug.wrappers.Response
    :param datetime.datetime last_modified: last modification date of the response content
    :param str etag: some sort of checksum of the content (deep etag)
    :return: the response object provided
    :rtype: werkzeug.wrappers.Response
    """
    response.cache_control.must_revalidate = True
    response.cache_control.max_age = max_age
    if last_modified:
        response.last_modified = last_modified
    if etag:
        response.set_etag(etag)
    return response.make_conditional(request.httprequest)

def _get_login_redirect_url(uid, redirect=None):
    """ Decide if user requires a specific post-login redirect, e.g. for 2FA, or if they are
    fully logged and can proceed to the requested URL
    """
    if request.session.uid: # fully logged
        return redirect or '/web'

    # partial session (MFA)
    url = request.env(user=uid)['res.users'].browse(uid)._mfa_url()
    if not redirect:
        return url

    parsed = werkzeug.urls.url_parse(url)
    qs = parsed.decode_query()
    qs['redirect'] = redirect
    return parsed.replace(query=werkzeug.urls.url_encode(qs)).to_url()

def login_and_redirect(db, login, key, redirect_url='/web'):
    uid = request.session.authenticate(db, login, key)
    redirect_url = _get_login_redirect_url(uid, redirect_url)
    return set_cookie_and_redirect(redirect_url)

def set_cookie_and_redirect(redirect_url):
    redirect = request.redirect(redirect_url, 303)
    redirect.autocorrect_location_header = False
    return redirect

def clean_action(action, env):
    action_type = action.setdefault('type', 'ir.actions.act_window_close')
    if action_type == 'ir.actions.act_window':
        action = fix_view_modes(action)

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

# I think generate_views,fix_view_modes should go into js ActionManager
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

def fix_view_modes(action):
    """ For historical reasons, Odoo has weird dealings in relation to
    view_mode and the view_type attribute (on window actions):

    * one of the view modes is ``tree``, which stands for both list views
      and tree views
    * the choice is made by checking ``view_type``, which is either
      ``form`` for a list view or ``tree`` for an actual tree view

    This methods simply folds the view_type into view_mode by adding a
    new view mode ``list`` which is the result of the ``tree`` view_mode
    in conjunction with the ``form`` view_type.

    TODO: this should go into the doc, some kind of "peculiarities" section

    :param dict action: an action descriptor
    :returns: nothing, the action is modified in place
    """
    if not action.get('views'):
        generate_views(action)

    if action.pop('view_type', 'form') != 'form':
        return action

    if 'view_mode' in action:
        action['view_mode'] = ','.join(
            mode if mode != 'tree' else 'list'
            for mode in action['view_mode'].split(','))
    action['views'] = [
        [id, mode if mode != 'tree' else 'list']
        for id, mode in action['views']
    ]

    return action

def _local_web_translations(trans_file):
    messages = []
    try:
        with open(trans_file) as t_file:
            po = babel.messages.pofile.read_po(t_file)
    except Exception:
        return
    for x in po:
        if x.id and x.string and "openerp-web" in x.auto_comments:
            messages.append({'id': x.id, 'string': x.string})
    return messages

def xml2json_from_elementtree(el, preserve_whitespaces=False):
    """ xml2json-direct
    Simple and straightforward XML-to-JSON converter in Python
    New BSD Licensed
    http://code.google.com/p/xml2json-direct/
    """
    res = {}
    if el.tag[0] == "{":
        ns, name = el.tag.rsplit("}", 1)
        res["tag"] = name
        res["namespace"] = ns[1:]
    else:
        res["tag"] = el.tag
    res["attrs"] = {}
    for k, v in el.items():
        res["attrs"][k] = v
    kids = []
    if el.text and (preserve_whitespaces or el.text.strip() != ''):
        kids.append(el.text)
    for kid in el:
        kids.append(xml2json_from_elementtree(kid, preserve_whitespaces))
        if kid.tail and (preserve_whitespaces or kid.tail.strip() != ''):
            kids.append(kid.tail)
    res["children"] = kids
    return res

class HomeStaticTemplateHelpers(object):
    """
    Helper Class that wraps the reading of static qweb templates files
    and xpath inheritance applied to those templates
    /!\ Template inheritance order is defined by ir.module.module natural order
        which is "sequence, name"
        Then a topological sort is applied, which just puts dependencies
        of a module before that module
    """
    NAME_TEMPLATE_DIRECTIVE = 't-name'
    STATIC_INHERIT_DIRECTIVE = 't-inherit'
    STATIC_INHERIT_MODE_DIRECTIVE = 't-inherit-mode'
    PRIMARY_MODE = 'primary'
    EXTENSION_MODE = 'extension'
    DEFAULT_MODE = PRIMARY_MODE

    def __init__(self, addons, db, checksum_only=False, debug=False):
        '''
        :param str|list addons: plain list or comma separated list of addons
        :param str db: the current db we are working on
        :param bool checksum_only: only computes the checksum of all files for addons
        :param str debug: the debug mode of the session
        '''
        super(HomeStaticTemplateHelpers, self).__init__()
        self.addons = addons.split(',') if isinstance(addons, str) else addons
        self.db = db
        self.debug = debug
        self.checksum_only = checksum_only
        self.template_dict = OrderedDict()

    def _get_parent_template(self, addon, template):
        """Computes the real addon name and the template name
        of the parent template (the one that is inherited from)

        :param str addon: the addon the template is declared in
        :param etree template: the current template we are are handling
        :returns: (str, str)
        """
        original_template_name = template.attrib[self.STATIC_INHERIT_DIRECTIVE]
        split_name_attempt = original_template_name.split('.', 1)
        parent_addon, parent_name = tuple(split_name_attempt) if len(split_name_attempt) == 2 else (addon, original_template_name)
        if parent_addon not in self.template_dict:
            if original_template_name in self.template_dict[addon]:
                parent_addon = addon
                parent_name = original_template_name
            else:
                raise ValueError(_('Module %s not loaded or inexistent, or templates of addon being loaded (%s) are misordered') % (parent_addon, addon))

        if parent_name not in self.template_dict[parent_addon]:
            raise ValueError(_("No template found to inherit from. Module %s and template name %s") % (parent_addon, parent_name))

        return parent_addon, parent_name

    def _compute_xml_tree(self, addon, file_name, source):
        """Computes the xml tree that 'source' contains
        Applies inheritance specs in the process

        :param str addon: the current addon we are reading files for
        :param str file_name: the current name of the file we are reading
        :param str source: the content of the file
        :returns: etree
        """
        try:
            all_templates_tree = etree.parse(io.BytesIO(source), parser=etree.XMLParser(remove_comments=True)).getroot()
        except etree.ParseError as e:
            _logger.error("Could not parse file %s: %s" % (file_name, e.msg))
            raise e

        self.template_dict.setdefault(addon, OrderedDict())
        for template_tree in list(all_templates_tree):
            if self.NAME_TEMPLATE_DIRECTIVE in template_tree.attrib:
                template_name = template_tree.attrib[self.NAME_TEMPLATE_DIRECTIVE]
                dotted_names = template_name.split('.', 1)
                if len(dotted_names) > 1 and dotted_names[0] == addon:
                    template_name = dotted_names[1]
            else:
                # self.template_dict[addon] grows after processing each template
                template_name = 'anonymous_template_%s' % len(self.template_dict[addon])
            if self.STATIC_INHERIT_DIRECTIVE in template_tree.attrib:
                inherit_mode = template_tree.attrib.get(self.STATIC_INHERIT_MODE_DIRECTIVE, self.DEFAULT_MODE)
                if inherit_mode not in [self.PRIMARY_MODE, self.EXTENSION_MODE]:
                    raise ValueError(_("Invalid inherit mode. Module %s and template name %s") % (addon, template_name))

                parent_addon, parent_name = self._get_parent_template(addon, template_tree)

                # After several performance tests, we found out that deepcopy is the most efficient
                # solution in this case (compared with copy, xpath with '.' and stringifying).
                parent_tree = copy.deepcopy(self.template_dict[parent_addon][parent_name])

                xpaths = list(template_tree)
                # owl chokes on comments, disable debug comments for now
                # pylint: disable=W0125
                if False: # self.debug and inherit_mode == self.EXTENSION_MODE:
                    for xpath in xpaths:
                        xpath.insert(0, etree.Comment(" Modified by %s from %s " % (template_name, addon)))
                elif inherit_mode == self.PRIMARY_MODE:
                    parent_tree.tag = template_tree.tag
                inherited_template = apply_inheritance_specs(parent_tree, xpaths)

                if inherit_mode == self.PRIMARY_MODE:  # New template_tree: A' = B(A)
                    for attr_name, attr_val in template_tree.attrib.items():
                        if attr_name not in ('t-inherit', 't-inherit-mode'):
                            inherited_template.set(attr_name, attr_val)
                    if self.debug:
                        self._remove_inheritance_comments(inherited_template)
                    self.template_dict[addon][template_name] = inherited_template

                else:  # Modifies original: A = B(A)
                    self.template_dict[parent_addon][parent_name] = inherited_template
            else:
                if template_name in self.template_dict[addon]:
                    raise ValueError(_("Template %s already exists in module %s") % (template_name, addon))
                self.template_dict[addon][template_name] = template_tree
        return all_templates_tree

    def _remove_inheritance_comments(self, inherited_template):
        '''Remove the comments added in the template already, they come from other templates extending
        the base of this inheritance

        :param inherited_template:
        '''
        for comment in inherited_template.xpath('//comment()'):
            if re.match(COMMENT_PATTERN, comment.text.strip()):
                comment.getparent().remove(comment)

    def _read_addon_file(self, path_or_url):
        """Read the content of a file or an ``ir.attachment`` record given by
        ``path_or_url``.

        :param str path_or_url:
        :returns: bytes
        :raises FileNotFoundError: if the path does not match a module file
            or an attachment
        """
        try:
            with file_open(path_or_url, 'rb') as fp:
                contents = fp.read()
        except FileNotFoundError as e:
            attachment = request.env['ir.attachment'].sudo().search([
                ('url', '=', path_or_url),
                ('type', '=', 'binary'),
            ], limit=1)
            if attachment:
                contents = attachment.raw
            else:
                raise e
        return contents

    def _concat_xml(self, file_dict):
        """Concatenate xml files

        :param dict(list) file_dict:
            key: addon name
            value: list of files for an addon
        :returns: (concatenation_result, checksum)
        :rtype: (bytes, str)
        """
        checksum = hashlib.new('sha512')  # sha512/256
        if not file_dict:
            return b'', checksum.hexdigest()

        root = None
        for addon, fnames in file_dict.items():
            for fname in fnames:
                contents = self._read_addon_file(fname)
                checksum.update(contents)
                if not self.checksum_only:
                    xml = self._compute_xml_tree(addon, fname, contents)

                    if root is None:
                        root = etree.Element('templates')

        for addon in self.template_dict.values():
            for template in addon.values():
                root.append(template)

        return etree.tostring(root, encoding='utf-8') if root is not None else b'', checksum.hexdigest()[:64]

    def _get_asset_paths(self, bundle):
        """Proxy for ir_asset._get_asset_paths
        Useful to make 'self' testable.
        """
        return request.env['ir.asset']._get_asset_paths(addons=self.addons, bundle=bundle, xml=True)

    def _get_qweb_templates(self, bundle):
        """One and only entry point that gets and evaluates static qweb templates

        :rtype: (str, str)
        """
        xml_paths = defaultdict(list)

        # group paths by module, keeping them in order
        for path, addon, _ in self._get_asset_paths(bundle):
            addon_paths = xml_paths[addon]
            if path not in addon_paths:
                addon_paths.append(path)

        content, checksum = self._concat_xml(xml_paths)
        return content, checksum

    @classmethod
    def get_qweb_templates_checksum(cls, addons=None, db=None, debug=False, bundle=None):
        return cls(addons, db, checksum_only=True, debug=debug)._get_qweb_templates(bundle)[1]

    @classmethod
    def get_qweb_templates(cls, addons=None, db=None, debug=False, bundle=None):
        return cls(addons, db, debug=debug)._get_qweb_templates(bundle)[0]

# Shared parameters for all login/signup flows
SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang'}

class GroupsTreeNode:
    """
    This class builds an ordered tree of groups from the result of a `read_group(lazy=False)`.
    The `read_group` returns a list of dictionnaries and each dictionnary is used to
    build a leaf. The entire tree is built by inserting all leaves.
    """

    def __init__(self, model, fields, groupby, groupby_type, root=None):
        self._model = model
        self._export_field_names = fields  # exported field names (e.g. 'journal_id', 'account_id/name', ...)
        self._groupby = groupby
        self._groupby_type = groupby_type

        self.count = 0  # Total number of records in the subtree
        self.children = OrderedDict()
        self.data = []  # Only leaf nodes have data

        if root:
            self.insert_leaf(root)

    def _get_aggregate(self, field_name, data, group_operator):
        # When exporting one2many fields, multiple data lines might be exported for one record.
        # Blank cells of additionnal lines are filled with an empty string. This could lead to '' being
        # aggregated with an integer or float.
        data = (value for value in data if value != '')

        if group_operator == 'avg':
            return self._get_avg_aggregate(field_name, data)

        aggregate_func = OPERATOR_MAPPING.get(group_operator)
        if not aggregate_func:
            _logger.warning("Unsupported export of group_operator '%s' for field %s on model %s" % (group_operator, field_name, self._model._name))
            return

        if self.data:
            return aggregate_func(data)
        return aggregate_func((child.aggregated_values.get(field_name) for child in self.children.values()))

    def _get_avg_aggregate(self, field_name, data):
        aggregate_func = OPERATOR_MAPPING.get('sum')
        if self.data:
            return aggregate_func(data) / self.count
        children_sums = (child.aggregated_values.get(field_name) * child.count for child in self.children.values())
        return aggregate_func(children_sums) / self.count

    def _get_aggregated_field_names(self):
        """ Return field names of exported field having a group operator """
        aggregated_field_names = []
        for field_name in self._export_field_names:
            if field_name == '.id':
                field_name = 'id'
            if '/' in field_name:
                # Currently no support of aggregated value for nested record fields
                # e.g. line_ids/analytic_line_ids/amount
                continue
            field = self._model._fields[field_name]
            if field.group_operator:
                aggregated_field_names.append(field_name)
        return aggregated_field_names

    # Lazy property to memoize aggregated values of children nodes to avoid useless recomputations
    @lazy_property
    def aggregated_values(self):

        aggregated_values = {}

        # Transpose the data matrix to group all values of each field in one iterable
        field_values = zip(*self.data)
        for field_name in self._export_field_names:
            field_data = self.data and next(field_values) or []

            if field_name in self._get_aggregated_field_names():
                field = self._model._fields[field_name]
                aggregated_values[field_name] = self._get_aggregate(field_name, field_data, field.group_operator)

        return aggregated_values

    def child(self, key):
        """
        Return the child identified by `key`.
        If it doesn't exists inserts a default node and returns it.
        :param key: child key identifier (groupby value as returned by read_group,
                    usually (id, display_name))
        :return: the child node
        """
        if key not in self.children:
            self.children[key] = GroupsTreeNode(self._model, self._export_field_names, self._groupby, self._groupby_type)
        return self.children[key]

    def insert_leaf(self, group):
        """
        Build a leaf from `group` and insert it in the tree.
        :param group: dict as returned by `read_group(lazy=False)`
        """
        leaf_path = [group.get(groupby_field) for groupby_field in self._groupby]
        domain = group.pop('__domain')
        count = group.pop('__count')

        records = self._model.search(domain, offset=0, limit=False, order=False)

        # Follow the path from the top level group to the deepest
        # group which actually contains the records' data.
        node = self # root
        node.count += count
        for node_key in leaf_path:
            # Go down to the next node or create one if it does not exist yet.
            node = node.child(node_key)
            # Update count value and aggregated value.
            node.count += count

        node.data = records.export_data(self._export_field_names).get('datas',[])


class ExportXlsxWriter:

    def __init__(self, field_names, row_count=0):
        self.field_names = field_names
        self.output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.output, {'in_memory': True})
        self.base_style = self.workbook.add_format({'text_wrap': True})
        self.header_style = self.workbook.add_format({'bold': True})
        self.header_bold_style = self.workbook.add_format({'text_wrap': True, 'bold': True, 'bg_color': '#e9ecef'})
        self.date_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd'})
        self.datetime_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.worksheet = self.workbook.add_worksheet()
        self.value = False

        if row_count > self.worksheet.xls_rowmax:
            raise UserError(_('There are too many rows (%s rows, limit: %s) to export as Excel 2007-2013 (.xlsx) format. Consider splitting the export.') % (row_count, self.worksheet.xls_rowmax))

    def __enter__(self):
        self.write_header()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def write_header(self):
        # Write main header
        for i, fieldname in enumerate(self.field_names):
            self.write(0, i, fieldname, self.header_style)
        self.worksheet.set_column(0, i, 30) # around 220 pixels

    def close(self):
        self.workbook.close()
        with self.output:
            self.value = self.output.getvalue()

    def write(self, row, column, cell_value, style=None):
        self.worksheet.write(row, column, cell_value, style)

    def write_cell(self, row, column, cell_value):
        cell_style = self.base_style

        if isinstance(cell_value, bytes):
            try:
                # because xlsx uses raw export, we can get a bytes object
                # here. xlsxwriter does not support bytes values in Python 3 ->
                # assume this is base64 and decode to a string, if this
                # fails note that you can't export
                cell_value = pycompat.to_text(cell_value)
            except UnicodeDecodeError:
                raise UserError(_("Binary fields can not be exported to Excel unless their content is base64-encoded. That does not seem to be the case for %s.", self.field_names)[column])

        if isinstance(cell_value, str):
            if len(cell_value) > self.worksheet.xls_strmax:
                cell_value = _("The content of this cell is too long for an XLSX file (more than %s characters). Please use the CSV format for this export.", self.worksheet.xls_strmax)
            else:
                cell_value = cell_value.replace("\r", " ")
        elif isinstance(cell_value, datetime.datetime):
            cell_style = self.datetime_style
        elif isinstance(cell_value, datetime.date):
            cell_style = self.date_style
        self.write(row, column, cell_value, cell_style)

class GroupExportXlsxWriter(ExportXlsxWriter):

    def __init__(self, fields, row_count=0):
        super().__init__([f['label'].strip() for f in fields], row_count)
        self.fields = fields

    def write_group(self, row, column, group_name, group, group_depth=0):
        group_name = group_name[1] if isinstance(group_name, tuple) and len(group_name) > 1 else group_name
        if group._groupby_type[group_depth] != 'boolean':
            group_name = group_name or _("Undefined")
        row, column = self._write_group_header(row, column, group_name, group, group_depth)

        # Recursively write sub-groups
        for child_group_name, child_group in group.children.items():
            row, column = self.write_group(row, column, child_group_name, child_group, group_depth + 1)

        for record in group.data:
            row, column = self._write_row(row, column, record)
        return row, column

    def _write_row(self, row, column, data):
        for value in data:
            self.write_cell(row, column, value)
            column += 1
        return row + 1, 0

    def _write_group_header(self, row, column, label, group, group_depth=0):
        aggregates = group.aggregated_values

        label = '%s%s (%s)' % ('    ' * group_depth, label, group.count)
        self.write(row, column, label, self.header_bold_style)
        if any(f.get('type') == 'monetary' for f in self.fields[1:]):

            decimal_places = [res['decimal_places'] for res in group._model.env['res.currency'].search_read([], ['decimal_places'])]
            decimal_places = max(decimal_places) if decimal_places else 2
        for field in self.fields[1:]: # No aggregates allowed in the first column because of the group title
            column += 1
            aggregated_value = aggregates.get(field['name'])
            # Float fields may not be displayed properly because of float
            # representation issue with non stored fields or with values
            # that, even stored, cannot be rounded properly and it is not
            # acceptable to display useless digits (i.e. monetary)
            #
            # non stored field ->  we force 2 digits
            # stored monetary -> we force max digits of installed currencies
            if isinstance(aggregated_value, float):
                if field.get('type') == 'monetary':
                    aggregated_value = float_repr(aggregated_value, decimal_places)
                elif not field.get('store'):
                    aggregated_value = float_repr(aggregated_value, 2)
            self.write(row, column, str(aggregated_value if aggregated_value is not None else ''), self.header_bold_style)
        return row + 1, 0


#----------------------------------------------------------
# Odoo Web web Controllers
#----------------------------------------------------------
class Home(http.Controller):

    @http.route('/', type='http', auth="none")
    def index(self, s_action=None, db=None, **kw):
        return request.redirect_query('/web', query=request.params)

    # ideally, this route should be `auth="user"` but that don't work in non-monodb mode.
    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        if not request.session.uid:
            return request.redirect('/web/login', 303)
        if kw.get('redirect'):
            return request.redirect(kw.get('redirect'), 303)

        request.uid = request.session.uid
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            response = request.render('web.webclient_bootstrap', qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except AccessError:
            return request.redirect('/web/login?error=access')

    @http.route('/web/webclient/load_menus/<string:unique>', type='http', auth='user', methods=['GET'])
    def web_load_menus(self, unique):
        """
        Loads the menus for the webclient
        :param unique: this parameters is not used, but mandatory: it is used by the HTTP stack to make a unique request
        :return: the menus (including the images in Base64)
        """
        menus = request.env["ir.ui.menu"].load_web_menus(request.session.debug)
        body = json.dumps(menus, default=ustr)
        response = request.make_response(body, [
            # this method must specify a content-type application/json instead of using the default text/html set because
            # the type of the route is set to HTTP, but the rpc is made with a get and expects JSON
            ('Content-Type', 'application/json'),
            ('Cache-Control', 'public, max-age=' + str(CONTENT_MAXAGE)),
        ])
        return response

    def _login_redirect(self, uid, redirect=None):
        return _get_login_redirect_url(uid, redirect)

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = {k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            try:
                uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True
                return request.redirect(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route('/web/become', type='http', auth='user', sitemap=False)
    def switch_to_admin(self):
        uid = request.env.user.id
        if request.env.user._is_system():
            uid = request.session.uid = odoo.SUPERUSER_ID
            # invalidate session token cache as we've changed the uid
            request.env['res.users'].clear_caches()
            request.session.session_token = security.compute_session_token(request.session, request.env)

        return request.redirect(self._login_redirect(uid))

    @http.route('/web/health', type='http', auth='none', save_session=False)
    def health(self):
        data = json.dumps({
            'status': 'pass',
        })
        headers = [('Content-Type', 'application/json'),
                   ('Cache-Control', 'no-store')]
        return request.make_response(data, headers)


class WebClient(http.Controller):

    @http.route('/web/webclient/locale/<string:lang>', type='http', auth="none")
    def load_locale(self, lang):
        magic_file_finding = [lang.replace("_", '-').lower(), lang.split('_')[0]]
        for code in magic_file_finding:
            try:
                return http.Response(
                    werkzeug.wsgi.wrap_file(
                        request.httprequest.environ,
                        file_open('web/static/lib/moment/locale/%s.js' % code, 'rb')
                    ),
                    content_type='application/javascript; charset=utf-8',
                    headers=[('Cache-Control', 'max-age=%s' % http.STATIC_CACHE)],
                    direct_passthrough=True,
                )
            except IOError:
                _logger.debug("No moment locale for code %s", code)

        return request.make_response("", headers=[
            ('Content-Type', 'application/javascript'),
            ('Cache-Control', 'max-age=%s' % http.STATIC_CACHE),
        ])

    @http.route('/web/webclient/qweb/<string:unique>', type='http', auth="none", cors="*")
    def qweb(self, unique, mods=None, db=None, bundle=None):

        if not request.db and mods is None:
            mods = odoo.conf.server_wide_modules or []

        content = HomeStaticTemplateHelpers.get_qweb_templates(mods, db, debug=request.session.debug, bundle=bundle)

        return request.make_response(content, [
                ('Content-Type', 'text/xml'),
                ('Cache-Control','public, max-age=' + str(CONTENT_MAXAGE))
            ])

    @http.route('/web/webclient/bootstrap_translations', type='json', auth="none")
    def bootstrap_translations(self, mods=None):
        """ Load local translations from *.po files, as a temporary solution
            until we have established a valid session. This is meant only
            for translating the login page and db management chrome, using
            the browser's language. """
        # For performance reasons we only load a single translation, so for
        # sub-languages (that should only be partially translated) we load the
        # main language PO instead - that should be enough for the login screen.
        context = dict(request.context)
        request.session._fix_lang(context)
        lang = context['lang'].split('_')[0]

        if mods is None:
            mods = odoo.conf.server_wide_modules or []
            if request.db:
                mods = request.env.registry._init_modules | set(mods)

        translations_per_module = {}
        for addon_name in mods:
            manifest = http.addons_manifest.get(addon_name)
            if manifest and manifest.get('bootstrap'):
                addons_path = http.addons_manifest[addon_name]['addons_path']
                f_name = os.path.join(addons_path, addon_name, "i18n", lang + ".po")
                if not os.path.exists(f_name):
                    continue
                translations_per_module[addon_name] = {'messages': _local_web_translations(f_name)}

        return {"modules": translations_per_module,
                "lang_parameters": None}

    @http.route('/web/webclient/translations/<string:unique>', type='http', auth="public", cors="*")
    def translations(self, unique, mods=None, lang=None):
        """
        Load the translations for the specified language and modules

        :param unique: this parameters is not used, but mandatory: it is used by the HTTP stack to make a unique request
        :param mods: the modules, a comma separated list
        :param lang: the language of the user
        :return:
        """
        request.disable_db = False

        if mods:
            mods = mods.split(',')
        elif mods is None:
            mods = list(request.env.registry._init_modules) + (odoo.conf.server_wide_modules or [])

        translations_per_module, lang_params = request.env["ir.translation"].get_translations_for_webclient(mods, lang)

        body = json.dumps({
            'lang': lang,
            'lang_parameters': lang_params,
            'modules': translations_per_module,
            'multi_lang': len(request.env['res.lang'].sudo().get_installed()) > 1,
        })
        response = request.make_response(body, [
            # this method must specify a content-type application/json instead of using the default text/html set because
            # the type of the route is set to HTTP, but the rpc is made with a get and expects JSON
            ('Content-Type', 'application/json'),
            ('Cache-Control', 'public, max-age=' + str(CONTENT_MAXAGE)),
        ])
        return response

    @http.route('/web/webclient/version_info', type='json', auth="none")
    def version_info(self):
        return odoo.service.common.exp_version()

    @http.route('/web/tests', type='http', auth="user")
    def test_suite(self, mod=None, **kwargs):
        return request.render('web.qunit_suite')

    @http.route('/web/tests/mobile', type='http', auth="none")
    def test_mobile_suite(self, mod=None, **kwargs):
        return request.render('web.qunit_mobile_suite')

    @http.route('/web/benchmarks', type='http', auth="none")
    def benchmarks(self, mod=None, **kwargs):
        return request.render('web.benchmark_suite')


class Proxy(http.Controller):

    @http.route('/web/proxy/post/<path:path>', type='http', auth='user', methods=['GET'])
    def post(self, path):
        """Effectively execute a POST request that was hooked through user login"""
        with request.session.load_request_data() as data:
            if not data:
                raise werkzeug.exceptions.BadRequest()
            from werkzeug.test import Client
            from werkzeug.wrappers import BaseResponse
            base_url = request.httprequest.base_url
            query_string = request.httprequest.query_string
            client = Client(http.root, BaseResponse)
            headers = {'X-Openerp-Session-Id': request.session.sid}
            return client.post('/' + path, base_url=base_url, query_string=query_string,
                               headers=headers, data=data)

class Database(http.Controller):

    def _render_template(self, **d):
        d.setdefault('manage',True)
        d['insecure'] = odoo.tools.config.verify_admin_password('admin')
        d['list_db'] = odoo.tools.config['list_db']
        d['langs'] = odoo.service.db.exp_list_lang()
        d['countries'] = odoo.service.db.exp_list_countries()
        d['pattern'] = DBNAME_PATTERN
        # databases list
        d['databases'] = []
        try:
            d['databases'] = http.db_list()
            d['incompatible_databases'] = odoo.service.db.list_db_incompatible(d['databases'])
        except odoo.exceptions.AccessDenied:
            monodb = db_monodb()
            if monodb:
                d['databases'] = [monodb]

        templates = {}

        with file_open("web/static/src/public/database_manager.qweb.html", "r") as fd:
            template = fd.read()
        with file_open("web/static/src/public/database_manager.master_input.qweb.html", "r") as fd:
            templates['master_input'] = fd.read()
        with file_open("web/static/src/public/database_manager.create_form.qweb.html", "r") as fd:
            templates['create_form'] = fd.read()

        def load(template_name, options):
            return (html.fragment_fromstring(templates[template_name]), template_name)

        return qweb_render(html.document_fromstring(template), d, load=load)

    @http.route('/web/database/selector', type='http', auth="none")
    def selector(self, **kw):
        request._cr = None
        return self._render_template(manage=False)

    @http.route('/web/database/manager', type='http', auth="none")
    def manager(self, **kw):
        request._cr = None
        return self._render_template()

    @http.route('/web/database/create', type='http', auth="none", methods=['POST'], csrf=False)
    def create(self, master_pwd, name, lang, password, **post):
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            if not re.match(DBNAME_PATTERN, name):
                raise Exception(_('Invalid database name. Only alphanumerical characters, underscore, hyphen and dot are allowed.'))
            # country code could be = "False" which is actually True in python
            country_code = post.get('country_code') or False
            dispatch_rpc('db', 'create_database', [master_pwd, name, bool(post.get('demo')), lang, password, post['login'], country_code, post['phone']])
            request.session.authenticate(name, post['login'], password)
            return request.redirect('/web')
        except Exception as e:
            error = "Database creation error: %s" % (str(e) or repr(e))
        return self._render_template(error=error)

    @http.route('/web/database/duplicate', type='http', auth="none", methods=['POST'], csrf=False)
    def duplicate(self, master_pwd, name, new_name):
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            if not re.match(DBNAME_PATTERN, new_name):
                raise Exception(_('Invalid database name. Only alphanumerical characters, underscore, hyphen and dot are allowed.'))
            dispatch_rpc('db', 'duplicate_database', [master_pwd, name, new_name])
            request._cr = None  # duplicating a database leads to an unusable cursor
            return request.redirect('/web/database/manager')
        except Exception as e:
            error = "Database duplication error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/drop', type='http', auth="none", methods=['POST'], csrf=False)
    def drop(self, master_pwd, name):
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            dispatch_rpc('db','drop', [master_pwd, name])
            request._cr = None  # dropping a database leads to an unusable cursor
            return request.redirect('/web/database/manager')
        except Exception as e:
            error = "Database deletion error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/backup', type='http', auth="none", methods=['POST'], csrf=False)
    def backup(self, master_pwd, name, backup_format = 'zip'):
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            odoo.service.db.check_super(master_pwd)
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            filename = "%s_%s.%s" % (name, ts, backup_format)
            headers = [
                ('Content-Type', 'application/octet-stream; charset=binary'),
                ('Content-Disposition', content_disposition(filename)),
            ]
            dump_stream = odoo.service.db.dump_db(name, None, backup_format)
            response = werkzeug.wrappers.Response(dump_stream, headers=headers, direct_passthrough=True)
            return response
        except Exception as e:
            _logger.exception('Database.backup')
            error = "Database backup error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/restore', type='http', auth="none", methods=['POST'], csrf=False)
    def restore(self, master_pwd, backup_file, name, copy=False):
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            data_file = None
            db.check_super(master_pwd)
            with tempfile.NamedTemporaryFile(delete=False) as data_file:
                backup_file.save(data_file)
            db.restore_db(name, data_file.name, str2bool(copy))
            return request.redirect('/web/database/manager')
        except Exception as e:
            error = "Database restore error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)
        finally:
            if data_file:
                os.unlink(data_file.name)

    @http.route('/web/database/change_password', type='http', auth="none", methods=['POST'], csrf=False)
    def change_password(self, master_pwd, master_pwd_new):
        try:
            dispatch_rpc('db', 'change_admin_password', [master_pwd, master_pwd_new])
            return request.redirect('/web/database/manager')
        except Exception as e:
            error = "Master password update error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/list', type='json', auth='none')
    def list(self):
        """
        Used by Mobile application for listing database
        :return: List of databases
        :rtype: list
        """
        return http.db_list()

class Session(http.Controller):

    @http.route('/web/session/get_session_info', type='json', auth="none")
    def get_session_info(self):
        request.session.check_security()
        request.uid = request.session.uid
        request.disable_db = False
        return request.env['ir.http'].session_info()

    @http.route('/web/session/authenticate', type='json', auth="none")
    def authenticate(self, db, login, password, base_location=None):
        request.session.authenticate(db, login, password)
        return request.env['ir.http'].session_info()

    @http.route('/web/session/change_password', type='json', auth="user")
    def change_password(self, fields):
        old_password, new_password,confirm_password = operator.itemgetter('old_pwd', 'new_password','confirm_pwd')(
            {f['name']: f['value'] for f in fields})
        if not (old_password.strip() and new_password.strip() and confirm_password.strip()):
            return {'error': _('You cannot leave any password empty.')}
        if new_password != confirm_password:
            return {'error': _('The new password and its confirmation must be identical.')}

        msg = _("Error, password not changed !")
        try:
            if request.env['res.users'].change_password(old_password, new_password):
                return {'new_password': new_password}
        except AccessDenied as e:
            msg = e.args[0]
            if msg == AccessDenied().args[0]:
                msg = _('The old password you provided is incorrect, your password was not changed.')
        except UserError as e:
            msg = e.args[0]
        return {'error': msg}

    @http.route('/web/session/get_lang_list', type='json', auth="none")
    def get_lang_list(self):
        try:
            return dispatch_rpc('db', 'list_lang', []) or []
        except Exception as e:
            return {"error": e, "title": _("Languages")}

    @http.route('/web/session/modules', type='json', auth="user")
    def modules(self):
        # return all installed modules. Web client is smart enough to not load a module twice
        return list(request.env.registry._init_modules | set([module.current_test] if module.current_test else []))

    @http.route('/web/session/save_session_action', type='json', auth="user")
    def save_session_action(self, the_action):
        """
        This method store an action object in the session object and returns an integer
        identifying that action. The method get_session_action() can be used to get
        back the action.

        :param the_action: The action to save in the session.
        :type the_action: anything
        :return: A key identifying the saved action.
        :rtype: integer
        """
        return request.session.save_action(the_action)

    @http.route('/web/session/get_session_action', type='json', auth="user")
    def get_session_action(self, key):
        """
        Gets back a previously saved action. This method can return None if the action
        was saved since too much time (this case should be handled in a smart way).

        :param key: The key given by save_session_action()
        :type key: integer
        :return: The saved action or None.
        :rtype: anything
        """
        return request.session.get_action(key)

    @http.route('/web/session/check', type='json', auth="user")
    def check(self):
        request.session.check_security()
        return None

    @http.route('/web/session/account', type='json', auth="user")
    def account(self):
        ICP = request.env['ir.config_parameter'].sudo()
        params = {
            'response_type': 'token',
            'client_id': ICP.get_param('database.uuid') or '',
            'state': json.dumps({'d': request.db, 'u': ICP.get_param('web.base.url')}),
            'scope': 'userinfo',
        }
        return 'https://accounts.odoo.com/oauth2/auth?' + url_encode(params)

    @http.route('/web/session/destroy', type='json', auth="user")
    def destroy(self):
        request.session.logout()

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        request.session.logout(keep_db=True)
        return request.redirect(redirect, 303)


class DataSet(http.Controller):

    @http.route('/web/dataset/search_read', type='json', auth="user")
    def search_read(self, model, fields=False, offset=0, limit=False, domain=None, sort=None):
        return self.do_search_read(model, fields, offset, limit, domain, sort)

    def do_search_read(self, model, fields=False, offset=0, limit=False, domain=None, sort=None):
        """ Performs a search() followed by a read() (if needed) using the
        provided search criteria

        :param str model: the name of the model to search on
        :param fields: a list of the fields to return in the result records
        :type fields: [str]
        :param int offset: from which index should the results start being returned
        :param int limit: the maximum number of records to return
        :param list domain: the search domain for the query
        :param list sort: sorting directives
        :returns: A structure (dict) with two keys: ids (all the ids matching
                  the (domain, context) pair) and records (paginated records
                  matching fields selection set)
        :rtype: list
        """
        Model = request.env[model]
        return Model.web_search_read(domain, fields, offset=offset, limit=limit, order=sort)

    @http.route('/web/dataset/load', type='json', auth="user")
    def load(self, model, id, fields):
        value = {}
        r = request.env[model].browse([id]).read()
        if r:
            value = r[0]
        return {'value': value}

    def call_common(self, model, method, args, domain_id=None, context_id=None):
        return self._call_kw(model, method, args, {})

    def _call_kw(self, model, method, args, kwargs):
        check_method_name(method)
        return call_kw(request.env[model], method, args, kwargs)

    @http.route('/web/dataset/call', type='json', auth="user")
    def call(self, model, method, args, domain_id=None, context_id=None):
        return self._call_kw(model, method, args, {})

    @http.route(['/web/dataset/call_kw', '/web/dataset/call_kw/<path:path>'], type='json', auth="user")
    def call_kw(self, model, method, args, kwargs, path=None):
        return self._call_kw(model, method, args, kwargs)

    @http.route('/web/dataset/call_button', type='json', auth="user")
    def call_button(self, model, method, args, kwargs):
        action = self._call_kw(model, method, args, kwargs)
        if isinstance(action, dict) and action.get('type') != '':
            return clean_action(action, env=request.env)
        return False

    @http.route('/web/dataset/resequence', type='json', auth="user")
    def resequence(self, model, ids, field='sequence', offset=0):
        """ Re-sequences a number of records in the model, by their ids

        The re-sequencing starts at the first model of ``ids``, the sequence
        number is incremented by one after each record and starts at ``offset``

        :param ids: identifiers of the records to resequence, in the new sequence order
        :type ids: list(id)
        :param str field: field used for sequence specification, defaults to
                          "sequence"
        :param int offset: sequence number for first record in ``ids``, allows
                           starting the resequencing from an arbitrary number,
                           defaults to ``0``
        """
        m = request.env[model]
        if not m.fields_get([field]):
            return False
        # python 2.6 has no start parameter
        for i, record in enumerate(m.browse(ids)):
            record.write({field: i + offset})
        return True

class View(http.Controller):

    @http.route('/web/view/edit_custom', type='json', auth="user")
    def edit_custom(self, custom_id, arch):
        """
        Edit a custom view

        :param int custom_id: the id of the edited custom view
        :param str arch: the edited arch of the custom view
        :returns: dict with acknowledged operation (result set to True)
        """
        custom_view = request.env['ir.ui.view.custom'].browse(custom_id)
        custom_view.write({ 'arch': arch })
        return {'result': True}

class Binary(http.Controller):

    @http.route(['/web/content',
        '/web/content/<string:xmlid>',
        '/web/content/<string:xmlid>/<string:filename>',
        '/web/content/<int:id>',
        '/web/content/<int:id>/<string:filename>',
        '/web/content/<string:model>/<int:id>/<string:field>',
        '/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'], type='http', auth="public")
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       filename=None, filename_field='name', unique=None, mimetype=None,
                       download=None, data=None, token=None, access_token=None, **kw):

        return request.env['ir.http']._get_content_common(xmlid=xmlid, model=model, res_id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype, access_token=access_token, token=token)

    @http.route(['/web/assets/debug/<string:filename>',
        '/web/assets/debug/<path:extra>/<string:filename>',
        '/web/assets/<int:id>/<string:filename>',
        '/web/assets/<int:id>-<string:unique>/<string:filename>',
        '/web/assets/<int:id>-<string:unique>/<path:extra>/<string:filename>'], type='http', auth="public")
    def content_assets(self, id=None, filename=None, unique=None, extra=None, **kw):
        id = id or request.env['ir.attachment'].sudo().search_read(
            [('url', '=like', f'/web/assets/%/{extra}/{filename}' if extra else f'/web/assets/%/{filename}')],
             fields=['id'], limit=1)[0]['id']

        return request.env['ir.http']._get_content_common(xmlid=None, model='ir.attachment', res_id=id, field='datas', unique=unique, filename=filename,
            filename_field='name', download=None, mimetype=None, access_token=None, token=None)

    @http.route(['/web/image',
        '/web/image/<string:xmlid>',
        '/web/image/<string:xmlid>/<string:filename>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<string:model>/<int:id>/<string:field>',
        '/web/image/<string:model>/<int:id>/<string:field>/<string:filename>',
        '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>',
        '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<int:id>',
        '/web/image/<int:id>/<string:filename>',
        '/web/image/<int:id>/<int:width>x<int:height>',
        '/web/image/<int:id>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<int:id>-<string:unique>',
        '/web/image/<int:id>-<string:unique>/<string:filename>',
        '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>',
        '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>'], type='http', auth="public")
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                      filename_field='name', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, access_token=None,
                      **kwargs):
        # other kwargs are ignored on purpose
        return request.env['ir.http']._content_image(xmlid=xmlid, model=model, res_id=id, field=field,
            filename_field=filename_field, unique=unique, filename=filename, mimetype=mimetype,
            download=download, width=width, height=height, crop=crop,
            quality=int(kwargs.get('quality', 0)), access_token=access_token)

    # backward compatibility
    @http.route(['/web/binary/image'], type='http', auth="public")
    def content_image_backward_compatibility(self, model, id, field, resize=None, **kw):
        width = None
        height = None
        if resize:
            width, height = resize.split(",")
        return request.env['ir.http']._content_image(model=model, res_id=id, field=field, width=width, height=height)

    @http.route('/web/binary/upload', type='http', auth="user")
    @serialize_exception
    def upload(self, ufile, callback=None):
        # TODO: might be useful to have a configuration flag for max-length file uploads
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        try:
            data = ufile.read()
            args = [len(data), ufile.filename,
                    ufile.content_type, pycompat.to_text(base64.b64encode(data))]
        except Exception as e:
            args = [False, str(e)]
        return out % (json.dumps(clean(callback)), json.dumps(args)) if callback else json.dumps(args)

    @http.route('/web/binary/upload_attachment', type='http', auth="user")
    @serialize_exception
    def upload_attachment(self, model, id, ufile, callback=None):
        files = request.httprequest.files.getlist('ufile')
        Model = request.env['ir.attachment']
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        args = []
        for ufile in files:

            filename = ufile.filename
            if request.httprequest.user_agent.browser == 'safari':
                # Safari sends NFD UTF-8 (where é is composed by 'e' and [accent])
                # we need to send it the same stuff, otherwise it'll fail
                filename = unicodedata.normalize('NFD', ufile.filename)

            try:
                attachment = Model.create({
                    'name': filename,
                    'datas': base64.encodebytes(ufile.read()),
                    'res_model': model,
                    'res_id': int(id)
                })
                attachment._post_add_create()
            except Exception:
                args.append({'error': _("Something horrible happened")})
                _logger.exception("Fail to upload attachment %s" % ufile.filename)
            else:
                args.append({
                    'filename': clean(filename),
                    'mimetype': ufile.content_type,
                    'id': attachment.id,
                    'size': attachment.file_size
                })
        return out % (json.dumps(clean(callback)), json.dumps(args)) if callback else json.dumps(args)

    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none", cors="*")
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        placeholder = functools.partial(get_resource_path, 'web', 'static', 'img')
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = odoo.SUPERUSER_ID

        if not dbname:
            response = http.send_file(placeholder(imgname + imgext))
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    company = int(kw['company']) if kw and kw.get('company') else False
                    if company:
                        cr.execute("""SELECT logo_web, write_date
                                        FROM res_company
                                       WHERE id = %s
                                   """, (company,))
                    else:
                        cr.execute("""SELECT c.logo_web, c.write_date
                                        FROM res_users u
                                   LEFT JOIN res_company c
                                          ON c.id = u.company_id
                                       WHERE u.id = %s
                                   """, (uid,))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_base64 = base64.b64decode(row[0])
                        image_data = io.BytesIO(image_base64)
                        mimetype = guess_mimetype(image_base64, default='image/png')
                        imgext = '.' + mimetype.split('/')[1]
                        if imgext == '.svg+xml':
                            imgext = '.svg'
                        response = http.send_file(image_data, filename=imgname + imgext, mimetype=mimetype, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname + imgext))

        return response

    @http.route(['/web/sign/get_fonts','/web/sign/get_fonts/<string:fontname>'], type='json', auth='public')
    def get_fonts(self, fontname=None):
        """This route will return a list of base64 encoded fonts.

        Those fonts will be proposed to the user when creating a signature
        using mode 'auto'.

        :return: base64 encoded fonts
        :rtype: list
        """
        supported_exts = ('.ttf', '.otf', '.woff', '.woff2')
        fonts = []
        fonts_directory = file_path(os.path.join('web', 'static', 'fonts', 'sign'))
        if fontname:
            font_path = os.path.join(fonts_directory, fontname)
            with file_open(font_path, 'rb', filter_ext=supported_exts) as font_file:
                font = base64.b64encode(font_file.read())
                fonts.append(font)
        else:
            font_filenames = sorted([fn for fn in os.listdir(fonts_directory) if fn.endswith(supported_exts)])
            for filename in font_filenames:
                font_file = file_open(os.path.join(fonts_directory, filename), 'rb', filter_ext=supported_exts)
                font = base64.b64encode(font_file.read())
                fonts.append(font)
        return fonts

class Action(http.Controller):

    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        Actions = request.env['ir.actions.actions']
        value = False
        try:
            action_id = int(action_id)
        except ValueError:
            try:
                action = request.env.ref(action_id)
                assert action._name.startswith('ir.actions.')
                action_id = action.id
            except Exception:
                action_id = 0   # force failed read

        base_action = Actions.browse([action_id]).sudo().read(['type'])
        if base_action:
            ctx = dict(request.context)
            action_type = base_action[0]['type']
            if action_type == 'ir.actions.report':
                ctx.update({'bin_size': True})
            if additional_context:
                ctx.update(additional_context)
            request.context = ctx
            action = request.env[action_type].sudo().browse([action_id]).read()
            if action:
                value = clean_action(action[0], env=request.env)
        return value

    @http.route('/web/action/run', type='json', auth="user")
    def run(self, action_id):
        action = request.env['ir.actions.server'].browse([action_id])
        result = action.run()
        return clean_action(result, env=action.env) if result else False

class Export(http.Controller):

    @http.route('/web/export/formats', type='json', auth="user")
    def formats(self):
        """ Returns all valid export formats

        :returns: for each export format, a pair of identifier and printable name
        :rtype: [(str, str)]
        """
        return [
            {'tag': 'xlsx', 'label': 'XLSX', 'error': None if xlsxwriter else "XlsxWriter 0.9.3 required"},
            {'tag': 'csv', 'label': 'CSV'},
        ]

    def fields_get(self, model):
        Model = request.env[model]
        fields = Model.fields_get()
        return fields

    @http.route('/web/export/get_fields', type='json', auth="user")
    def get_fields(self, model, prefix='', parent_name= '',
                   import_compat=True, parent_field_type=None,
                   parent_field=None, exclude=None):

        fields = self.fields_get(model)
        if import_compat:
            if parent_field_type in ['many2one', 'many2many']:
                rec_name = request.env[model]._rec_name_fallback()
                fields = {'id': fields['id'], rec_name: fields[rec_name]}
        else:
            fields['.id'] = {**fields['id']}

        fields['id']['string'] = _('External ID')

        if parent_field:
            parent_field['string'] = _('External ID')
            fields['id'] = parent_field

        fields_sequence = sorted(fields.items(),
            key=lambda field: odoo.tools.ustr(field[1].get('string', '').lower()))

        records = []
        for field_name, field in fields_sequence:
            if import_compat and not field_name == 'id':
                if exclude and field_name in exclude:
                    continue
                if field.get('readonly'):
                    # If none of the field's states unsets readonly, skip the field
                    if all(dict(attrs).get('readonly', True)
                           for attrs in field.get('states', {}).values()):
                        continue
            if not field.get('exportable', True):
                continue

            id = prefix + (prefix and '/'or '') + field_name
            val = id
            if field_name == 'name' and import_compat and parent_field_type in ['many2one', 'many2many']:
                # Add name field when expand m2o and m2m fields in import-compatible mode
                val = prefix
            name = parent_name + (parent_name and '/' or '') + field['string']
            record = {'id': id, 'string': name,
                      'value': val, 'children': False,
                      'field_type': field.get('type'),
                      'required': field.get('required'),
                      'relation_field': field.get('relation_field')}
            records.append(record)

            if len(id.split('/')) < 3 and 'relation' in field:
                ref = field.pop('relation')
                record['value'] += '/id'
                record['params'] = {'model': ref, 'prefix': id, 'name': name, 'parent_field': field}
                record['children'] = True

        return records

    @http.route('/web/export/namelist', type='json', auth="user")
    def namelist(self, model, export_id):
        # TODO: namelist really has no reason to be in Python (although itertools.groupby helps)
        export = request.env['ir.exports'].browse([export_id]).read()[0]
        export_fields_list = request.env['ir.exports.line'].browse(export['export_fields']).read()

        fields_data = self.fields_info(
            model, [f['name'] for f in export_fields_list])

        return [
            {'name': field['name'], 'label': fields_data[field['name']]}
            for field in export_fields_list
        ]

    def fields_info(self, model, export_fields):
        info = {}
        fields = self.fields_get(model)
        if ".id" in export_fields:
            fields['.id'] = fields.get('id', {'string': 'ID'})

        # To make fields retrieval more efficient, fetch all sub-fields of a
        # given field at the same time. Because the order in the export list is
        # arbitrary, this requires ordering all sub-fields of a given field
        # together so they can be fetched at the same time
        #
        # Works the following way:
        # * sort the list of fields to export, the default sorting order will
        #   put the field itself (if present, for xmlid) and all of its
        #   sub-fields right after it
        # * then, group on: the first field of the path (which is the same for
        #   a field and for its subfields and the length of splitting on the
        #   first '/', which basically means grouping the field on one side and
        #   all of the subfields on the other. This way, we have the field (for
        #   the xmlid) with length 1, and all of the subfields with the same
        #   base but a length "flag" of 2
        # * if we have a normal field (length 1), just add it to the info
        #   mapping (with its string) as-is
        # * otherwise, recursively call fields_info via graft_subfields.
        #   all graft_subfields does is take the result of fields_info (on the
        #   field's model) and prepend the current base (current field), which
        #   rebuilds the whole sub-tree for the field
        #
        # result: because we're not fetching the fields_get for half the
        # database models, fetching a namelist with a dozen fields (including
        # relational data) falls from ~6s to ~300ms (on the leads model).
        # export lists with no sub-fields (e.g. import_compatible lists with
        # no o2m) are even more efficient (from the same 6s to ~170ms, as
        # there's a single fields_get to execute)
        for (base, length), subfields in itertools.groupby(
                sorted(export_fields),
                lambda field: (field.split('/', 1)[0], len(field.split('/', 1)))):
            subfields = list(subfields)
            if length == 2:
                # subfields is a seq of $base/*rest, and not loaded yet
                info.update(self.graft_subfields(
                    fields[base]['relation'], base, fields[base]['string'],
                    subfields
                ))
            elif base in fields:
                info[base] = fields[base]['string']

        return info

    def graft_subfields(self, model, prefix, prefix_string, fields):
        export_fields = [field.split('/', 1)[1] for field in fields]
        return (
            (prefix + '/' + k, prefix_string + '/' + v)
            for k, v in self.fields_info(model, export_fields).items())

class ExportFormat(object):

    @property
    def content_type(self):
        """ Provides the format's content type """
        raise NotImplementedError()

    @property
    def extension(self):
        raise NotImplementedError()

    def filename(self, base):
        """ Creates a filename *without extension* for the item / format of
        model ``base``.
        """
        if base not in request.env:
            return base

        model_description = request.env['ir.model']._get(base).name
        return f"{model_description} ({base})"

    def from_data(self, fields, rows):
        """ Conversion method from Odoo's export data to whatever the
        current export class outputs

        :params list fields: a list of fields to export
        :params list rows: a list of records to export
        :returns:
        :rtype: bytes
        """
        raise NotImplementedError()

    def from_group_data(self, fields, groups):
        raise NotImplementedError()

    def base(self, data):
        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        Model = request.env[model].with_context(**params.get('context', {}))
        if not Model._is_an_ordinary_table():
            fields = [field for field in fields if field['name'] != 'id']

        field_names = [f['name'] for f in fields]
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        groupby = params.get('groupby')
        if not import_compat and groupby:
            groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
            domain = [('id', 'in', ids)] if ids else domain
            groups_data = Model.read_group(domain, [x if x != '.id' else 'id' for x in field_names], groupby, lazy=False)

            # read_group(lazy=False) returns a dict only for final groups (with actual data),
            # not for intermediary groups. The full group tree must be re-constructed.
            tree = GroupsTreeNode(Model, field_names, groupby, groupby_type)
            for leaf in groups_data:
                tree.insert_leaf(leaf)

            response_data = self.from_group_data(fields, tree)
        else:
            Model = Model.with_context(import_compat=import_compat)
            records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

            export_data = records.export_data(field_names).get('datas',[])
            response_data = self.from_data(columns_headers, export_data)

        # TODO: call `clean_filename` directly in `content_disposition`?
        return request.make_response(response_data,
            headers=[('Content-Disposition',
                            content_disposition(
                                osutil.clean_filename(self.filename(model) + self.extension))),
                     ('Content-Type', self.content_type)],
        )

class CSVExport(ExportFormat, http.Controller):

    @http.route('/web/export/csv', type='http', auth="user")
    @serialize_exception
    def index(self, data):
        return self.base(data)

    @property
    def content_type(self):
        return 'text/csv;charset=utf8'

    @property
    def extension(self):
        return '.csv'

    def from_group_data(self, fields, groups):
        raise UserError(_("Exporting grouped data to csv is not supported."))

    def from_data(self, fields, rows):
        fp = io.BytesIO()
        writer = pycompat.csv_writer(fp, quoting=1)

        writer.writerow(fields)

        for data in rows:
            row = []
            for d in data:
                # Spreadsheet apps tend to detect formulas on leading =, + and -
                if isinstance(d, str) and d.startswith(('=', '-', '+')):
                    d = "'" + d

                row.append(pycompat.to_text(d))
            writer.writerow(row)

        return fp.getvalue()

class ExcelExport(ExportFormat, http.Controller):

    @http.route('/web/export/xlsx', type='http', auth="user")
    @serialize_exception
    def index(self, data):
        return self.base(data)

    @property
    def content_type(self):
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    @property
    def extension(self):
        return '.xlsx'

    def from_group_data(self, fields, groups):
        with GroupExportXlsxWriter(fields, groups.count) as xlsx_writer:
            x, y = 1, 0
            for group_name, group in groups.children.items():
                x, y = xlsx_writer.write_group(x, y, group_name, group)

        return xlsx_writer.value

    def from_data(self, fields, rows):
        with ExportXlsxWriter(fields, len(rows)) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    if isinstance(cell_value, (list, tuple)):
                        cell_value = pycompat.to_text(cell_value)
                    xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

        return xlsx_writer.value


class ReportController(http.Controller):

    #------------------------------------------------------
    # Report controllers
    #------------------------------------------------------
    @http.route([
        '/report/<converter>/<reportname>',
        '/report/<converter>/<reportname>/<docids>',
    ], type='http', auth='user', website=True)
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report = request.env['ir.actions.report']._get_report_from_name(reportname)
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(',')]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            data['context'] = json.loads(data['context'])
            context.update(data['context'])
        if converter == 'html':
            html = report.with_context(context)._render_qweb_html(docids, data=data)[0]
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = report.with_context(context)._render_qweb_pdf(docids, data=data)[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        elif converter == 'text':
            text = report.with_context(context)._render_qweb_text(docids, data=data)[0]
            texthttpheaders = [('Content-Type', 'text/plain'), ('Content-Length', len(text))]
            return request.make_response(text, headers=texthttpheaders)
        else:
            raise werkzeug.exceptions.HTTPException(description='Converter %s not implemented.' % converter)

    #------------------------------------------------------
    # Misc. route utils
    #------------------------------------------------------
    @http.route(['/report/barcode', '/report/barcode/<type>/<path:value>'], type='http', auth="public")
    def report_barcode(self, type, value, **kwargs):
        """Contoller able to render barcode images thanks to reportlab.
        Samples::

            <img t-att-src="'/report/barcode/QR/%s' % o.name"/>
            <img t-att-src="'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s' %
                ('QR', o.name, 200, 200)"/>

        :param type: Accepted types: 'Codabar', 'Code11', 'Code128', 'EAN13', 'EAN8', 'Extended39',
        'Extended93', 'FIM', 'I2of5', 'MSI', 'POSTNET', 'QR', 'Standard39', 'Standard93',
        'UPCA', 'USPS_4State'
        :param width: Pixel width of the barcode
        :param height: Pixel height of the barcode
        :param humanreadable: Accepted values: 0 (default) or 1. 1 will insert the readable value
        at the bottom of the output image
        :param quiet: Accepted values: 0 (default) or 1. 1 will display white
        margins on left and right.
        :param mask: The mask code to be used when rendering this QR-code.
                     Masks allow adding elements on top of the generated image,
                     such as the Swiss cross in the center of QR-bill codes.
        :param barLevel: QR code Error Correction Levels. Default is 'L'.
        ref: https://hg.reportlab.com/hg-public/reportlab/file/830157489e00/src/reportlab/graphics/barcode/qr.py#l101
        """
        try:
            barcode = request.env['ir.actions.report'].barcode(type, value, **kwargs)
        except (ValueError, AttributeError):
            raise werkzeug.exceptions.HTTPException(description='Cannot convert into barcode.')

        return request.make_response(barcode, headers=[('Content-Type', 'image/png')])

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, context=None):
        """This function is used by 'action_manager_report.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with an attachment header

        """
        requestcontent = json.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        reportname = '???'
        try:
            if type in ['qweb-pdf', 'qweb-text']:
                converter = 'pdf' if type == 'qweb-pdf' else 'text'
                extension = 'pdf' if type == 'qweb-pdf' else 'txt'

                pattern = '/report/pdf/' if type == 'qweb-pdf' else '/report/text/'
                reportname = url.split(pattern)[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter=converter, context=context)
                else:
                    # Particular report:
                    data = dict(url_decode(url.split('?')[1]).items())  # decoding the args represented in JSON
                    if 'context' in data:
                        context, data_context = json.loads(context or '{}'), json.loads(data.pop('context'))
                        context = json.dumps({**context, **data_context})
                    response = self.report_routes(reportname, converter=converter, context=context, **data)

                report = request.env['ir.actions.report']._get_report_from_name(reportname)
                filename = "%s.%s" % (report.name, extension)

                if docids:
                    ids = [int(x) for x in docids.split(",")]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                response.headers.add('Content-Disposition', content_disposition(filename))
                return response
            else:
                return
        except Exception as e:
            _logger.exception("Error while generating report %s", reportname)
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))

    @http.route(['/report/check_wkhtmltopdf'], type='json', auth="user")
    def check_wkhtmltopdf(self):
        return request.env['ir.actions.report'].get_wkhtmltopdf_state()
