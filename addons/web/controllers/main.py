# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.messages.pofile
import base64
import datetime
import functools
import glob
import hashlib
import imghdr
import io
import itertools
import jinja2
import json
import logging
import operator
import os
import re
import sys
import tempfile
import time
import zlib

import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from collections import OrderedDict
from werkzeug.urls import url_decode, iri_to_uri
from xml.etree import ElementTree
import unicodedata


import odoo
import odoo.modules.registry
from odoo.api import call_kw, Environment
from odoo.modules import get_resource_path
from odoo.tools import crop_image, topological_sort, html_escape, pycompat
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.translate import _
from odoo.tools.misc import str2bool, xlwt, file_open
from odoo.tools.safe_eval import safe_eval
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
    serialize_exception as _serialize_exception, Response
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.models import check_method_name
from odoo.service import db, security

_logger = logging.getLogger(__name__)

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.web', "views")

env = jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps

# 1 week cache for asset bundles as advised by Google Page Speed
BUNDLE_MAXAGE = 60 * 60 * 24 * 7

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

#----------------------------------------------------------
# Odoo Web helpers
#----------------------------------------------------------

db_list = http.db_list

db_monodb = http.db_monodb

def serialize_exception(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            _logger.exception("An exception occured during an http request")
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return werkzeug.exceptions.InternalServerError(json.dumps(error))
    return wrap

def redirect_with_hash(*args, **kw):
    """
        .. deprecated:: 8.0

        Use the ``http.redirect_with_hash()`` function instead.
    """
    return http.redirect_with_hash(*args, **kw)

def abort_and_redirect(url):
    r = request.httprequest
    response = werkzeug.utils.redirect(url, 302)
    response = r.app.get_response(r, response, explicit_session=False)
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
        abort_and_redirect(url_redirect)

    # if db not provided, use the session one
    if not db and request.session.db and http.db_filter([request.session.db]):
        db = request.session.db

    # if no database provided and no database in session, use monodb
    if not db:
        db = db_monodb(request.httprequest)

    # if no db can be found til here, send to the database selector
    # the database selector will redirect to database manager if needed
    if not db:
        werkzeug.exceptions.abort(werkzeug.utils.redirect(redirect, 303))

    # always switch the session to the computed db
    if db != request.session.db:
        request.session.logout()
        abort_and_redirect(request.httprequest.url)

    request.session.db = db

def module_installed(environment):
    # Candidates module the current heuristic is the /static dir
    loadable = list(http.addons_manifest)

    # Retrieve database installed modules
    # TODO The following code should move to ir.module.module.list_installed_modules()
    Modules = environment['ir.module.module']
    domain = [('state','=','installed'), ('name','in', loadable)]
    modules = OrderedDict(
        (module.name, module.dependencies_id.mapped('name'))
        for module in Modules.search(domain)
    )

    sorted_modules = topological_sort(modules)
    return sorted_modules

def module_installed_bypass_session(dbname):
    try:
        registry = odoo.registry(dbname)
        with registry.cursor() as cr:
            return module_installed(
                environment=Environment(cr, odoo.SUPERUSER_ID, {}))
    except Exception:
        pass
    return {}

def module_boot(db=None):
    server_wide_modules = odoo.conf.server_wide_modules or []
    serverside = ['base', 'web']
    dbside = []
    for i in server_wide_modules:
        if i in http.addons_manifest and i not in serverside:
            serverside.append(i)
    monodb = db or db_monodb()
    if monodb:
        dbside = module_installed_bypass_session(monodb)
        dbside = [i for i in dbside if i not in serverside]
    addons = serverside + dbside
    return addons

def concat_xml(file_list):
    """Concatenate xml files

    :param list(str) file_list: list of files to check
    :returns: (concatenation_result, checksum)
    :rtype: (bytes, str)
    """
    checksum = hashlib.new('sha1')
    if not file_list:
        return b'', checksum.hexdigest()

    root = None
    for fname in file_list:
        with open(fname, 'rb') as fp:
            contents = fp.read()
            checksum.update(contents)
            fp.seek(0)
            try:
                xml = ElementTree.parse(fp).getroot()
            except ElementTree.ParseError as e:
                _logger.error("Could not parse file %s: %s" % (fname, e.msg))
                raise e

        if root is None:
            root = ElementTree.Element(xml.tag)
        #elif root.tag != xml.tag:
        #    raise ValueError("Root tags missmatch: %r != %r" % (root.tag, xml.tag))

        for child in xml.getchildren():
            root.append(child)
    return ElementTree.tostring(root, 'utf-8'), checksum.hexdigest()

def fs2web(path):
    """convert FS path into web path"""
    return '/'.join(path.split(os.path.sep))

def manifest_glob(extension, addons=None, db=None, include_remotes=False):
    if addons is None:
        addons = module_boot(db=db)
    else:
        addons = addons.split(',')
    r = []
    for addon in addons:
        manifest = http.addons_manifest.get(addon, None)
        if not manifest:
            continue
        # ensure does not ends with /
        addons_path = os.path.join(manifest['addons_path'], '')[:-1]
        globlist = manifest.get(extension, [])
        for pattern in globlist:
            if pattern.startswith(('http://', 'https://', '//')):
                if include_remotes:
                    r.append((None, pattern))
            else:
                for path in glob.glob(os.path.normpath(os.path.join(addons_path, addon, pattern))):
                    r.append((path, fs2web(path[len(addons_path):])))
    return r

def manifest_list(extension, mods=None, db=None, debug=None):
    """ list resources to load specifying either:
    mods: a comma separated string listing modules
    db: a database name (return all installed modules in that database)
    """
    if debug is not None:
        _logger.warning("odoo.addons.web.main.manifest_list(): debug parameter is deprecated")
    files = manifest_glob(extension, addons=mods, db=db, include_remotes=True)
    return [wp for _fp, wp in files]

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

def login_and_redirect(db, login, key, redirect_url='/web'):
    request.session.authenticate(db, login, key)
    return set_cookie_and_redirect(redirect_url)

def set_cookie_and_redirect(redirect_url):
    redirect = werkzeug.utils.redirect(redirect_url, 303)
    redirect.autocorrect_location_header = False
    return redirect

def clean_action(action):
    action.setdefault('flags', {})
    action_type = action.setdefault('type', 'ir.actions.act_window_close')
    if action_type == 'ir.actions.act_window':
        return fix_view_modes(action)
    return action

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

def binary_content(xmlid=None, model='ir.attachment', id=None, field='datas', unique=False,
                   filename=None, filename_field='datas_fname', download=False, mimetype=None,
                   default_mimetype='application/octet-stream', related_id=None, access_mode=None, access_token=None,
                   env=None):
    return request.registry['ir.http'].binary_content(
        xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
        filename_field=filename_field, download=download, mimetype=mimetype,
        default_mimetype=default_mimetype, related_id=related_id, access_mode=access_mode, access_token=access_token,
        env=env)

#----------------------------------------------------------
# Odoo Web web Controllers
#----------------------------------------------------------
class Home(http.Controller):

    @http.route('/', type='http', auth="none")
    def index(self, s_action=None, db=None, **kw):
        return http.local_redirect('/web', query=request.params, keep_hash=True)

    # ideally, this route should be `auth="user"` but that don't work in non-monodb mode.
    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        if not request.session.uid:
            return werkzeug.utils.redirect('/web/login', 303)
        if kw.get('redirect'):
            return werkzeug.utils.redirect(kw.get('redirect'), 303)

        request.uid = request.session.uid
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            response = request.render('web.webclient_bootstrap', qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except AccessError:
            return werkzeug.utils.redirect('/web/login?error=access')

    @http.route('/web/dbredirect', type='http', auth="none")
    def web_db_redirect(self, redirect='/', **kw):
        ensure_db()
        return werkzeug.utils.redirect(redirect, 303)

    def _login_redirect(self, uid, redirect=None):
        return redirect if redirect else '/web'

    @http.route('/web/login', type='http', auth="none", sitemap=False)
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            try:
                uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employee can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        # otherwise no real way to test debug mode in template as ?debug =>
        # values['debug'] = '' but that's also the fallback value when
        # missing variables in qweb
        if 'debug' in values:
            values['debug'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route('/web/become', type='http', auth='user', sitemap=False)
    def switch_to_admin(self):
        uid = request.env.user.id
        if request.env.user._is_system():
            uid = request.session.uid = odoo.SUPERUSER_ID
            request.env['res.users']._invalidate_session_cache()
            request.session.session_token = security.compute_session_token(request.session, request.env)

        return http.local_redirect(self._login_redirect(uid), keep_hash=True)

class WebClient(http.Controller):

    @http.route('/web/webclient/csslist', type='json', auth="none")
    def csslist(self, mods=None):
        return manifest_list('css', mods=mods)

    @http.route('/web/webclient/jslist', type='json', auth="none")
    def jslist(self, mods=None):
        return manifest_list('js', mods=mods)

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
                    headers=[('Cache-Control', 'max-age=36000')],
                    direct_passthrough=True,
                )
            except IOError:
                _logger.debug("No moment locale for code %s", code)

        return request.make_response("", headers=[
            ('Content-Type', 'application/javascript'),
            ('Cache-Control', 'max-age=36000'),
        ])

    @http.route('/web/webclient/qweb', type='http', auth="none", cors="*")
    def qweb(self, mods=None, db=None):
        files = [f[0] for f in manifest_glob('qweb', addons=mods, db=db)]
        last_modified = get_last_modified(files)
        if request.httprequest.if_modified_since and request.httprequest.if_modified_since >= last_modified:
            return werkzeug.wrappers.Response(status=304)

        content, checksum = concat_xml(files)

        return make_conditional(
            request.make_response(content, [('Content-Type', 'text/xml')]),
            last_modified, checksum)

    @http.route('/web/webclient/bootstrap_translations', type='json', auth="none")
    def bootstrap_translations(self, mods):
        """ Load local translations from *.po files, as a temporary solution
            until we have established a valid session. This is meant only
            for translating the login page and db management chrome, using
            the browser's language. """
        # For performance reasons we only load a single translation, so for
        # sub-languages (that should only be partially translated) we load the
        # main language PO instead - that should be enough for the login screen.
        lang = request.lang.split('_')[0]

        translations_per_module = {}
        for addon_name in mods:
            if http.addons_manifest[addon_name].get('bootstrap'):
                addons_path = http.addons_manifest[addon_name]['addons_path']
                f_name = os.path.join(addons_path, addon_name, "i18n", lang + ".po")
                if not os.path.exists(f_name):
                    continue
                translations_per_module[addon_name] = {'messages': _local_web_translations(f_name)}

        return {"modules": translations_per_module,
                "lang_parameters": None}

    @http.route('/web/webclient/translations', type='json', auth="none")
    def translations(self, mods=None, lang=None):
        request.disable_db = False
        if mods is None:
            mods = [x['name'] for x in request.env['ir.module.module'].sudo().search_read(
                [('state', '=', 'installed')], ['name'])]
        if lang is None:
            lang = request.context["lang"]
        langs = request.env['res.lang'].sudo().search([("code", "=", lang)])
        lang_params = None
        if langs:
            lang_params = langs.read([
                "name", "direction", "date_format", "time_format",
                "grouping", "decimal_point", "thousands_sep", "week_start"])[0]

        # Regional languages (ll_CC) must inherit/override their parent lang (ll), but this is
        # done server-side when the language is loaded, so we only need to load the user's lang.
        translations_per_module = {}
        messages = request.env['ir.translation'].sudo().search_read([
            ('module', 'in', mods), ('lang', '=', lang),
            ('comments', 'like', 'openerp-web'), ('value', '!=', False),
            ('value', '!=', '')],
            ['module', 'src', 'value', 'lang'], order='module')
        for mod, msg_group in itertools.groupby(messages, key=operator.itemgetter('module')):
            translations_per_module.setdefault(mod, {'messages': []})
            translations_per_module[mod]['messages'].extend({
                'id': m['src'],
                'string': m['value']}
                for m in msg_group)
        return {
            'lang_parameters': lang_params,
            'modules': translations_per_module,
            'multi_lang': len(request.env['res.lang'].sudo().get_installed()) > 1,
        }

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

    @http.route('/web/proxy/load', type='json', auth="none")
    def load(self, path):
        """ Proxies an HTTP request through a JSON request.

        It is strongly recommended to not request binary files through this,
        as the result will be a binary data blob as well.

        :param path: actual request path
        :return: file content
        """
        from werkzeug.test import Client
        from werkzeug.wrappers import BaseResponse

        base_url = request.httprequest.base_url
        return Client(request.httprequest.app, BaseResponse).get(path, base_url=base_url).data

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
            client = Client(request.httprequest.app, BaseResponse)
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
        return env.get_template("database_manager.html").render(d)

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
        try:
            if not re.match(DBNAME_PATTERN, name):
                raise Exception(_('Invalid database name. Only alphanumerical characters, underscore, hyphen and dot are allowed.'))
            # country code could be = "False" which is actually True in python
            country_code = post.get('country_code') or False
            dispatch_rpc('db', 'create_database', [master_pwd, name, bool(post.get('demo')), lang, password, post['login'], country_code, post['phone']])
            request.session.authenticate(name, post['login'], password)
            return http.local_redirect('/web/')
        except Exception as e:
            error = "Database creation error: %s" % (str(e) or repr(e))
        return self._render_template(error=error)

    @http.route('/web/database/duplicate', type='http', auth="none", methods=['POST'], csrf=False)
    def duplicate(self, master_pwd, name, new_name):
        try:
            if not re.match(DBNAME_PATTERN, new_name):
                raise Exception(_('Invalid database name. Only alphanumerical characters, underscore, hyphen and dot are allowed.'))
            dispatch_rpc('db', 'duplicate_database', [master_pwd, name, new_name])
            return http.local_redirect('/web/database/manager')
        except Exception as e:
            error = "Database duplication error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/drop', type='http', auth="none", methods=['POST'], csrf=False)
    def drop(self, master_pwd, name):
        try:
            dispatch_rpc('db','drop', [master_pwd, name])
            request._cr = None  # dropping a database leads to an unusable cursor
            return http.local_redirect('/web/database/manager')
        except Exception as e:
            error = "Database deletion error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/backup', type='http', auth="none", methods=['POST'], csrf=False)
    def backup(self, master_pwd, name, backup_format = 'zip'):
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
        try:
            data_file = None
            db.check_super(master_pwd)
            with tempfile.NamedTemporaryFile(delete=False) as data_file:
                backup_file.save(data_file)
            db.restore_db(name, data_file.name, str2bool(copy))
            return http.local_redirect('/web/database/manager')
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
            return http.local_redirect('/web/database/manager')
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
            return {'error':_('You cannot leave any password empty.'),'title': _('Change Password')}
        if new_password != confirm_password:
            return {'error': _('The new password and its confirmation must be identical.'),'title': _('Change Password')}

        msg = _("Error, password not changed !")
        try:
            if request.env['res.users'].change_password(old_password, new_password):
                return {'new_password':new_password}
        except UserError as e:
            msg = e.name
        except AccessDenied as e:
            msg = e.args[0]
            if msg == AccessDenied().args[0]:
                msg = _('The old password you provided is incorrect, your password was not changed.')
        return {'title': _('Change Password'), 'error': msg}

    @http.route('/web/session/get_lang_list', type='json', auth="none")
    def get_lang_list(self):
        try:
            return dispatch_rpc('db', 'list_lang', []) or []
        except Exception as e:
            return {"error": e, "title": _("Languages")}

    @http.route('/web/session/modules', type='json', auth="user")
    def modules(self):
        # return all installed modules. Web client is smart enough to not load a module twice
        return module_installed(environment=request.env(user=odoo.SUPERUSER_ID))

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
        return 'https://accounts.odoo.com/oauth2/auth?' + werkzeug.url_encode(params)

    @http.route('/web/session/destroy', type='json', auth="user")
    def destroy(self):
        request.session.logout()

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)


class DataSet(http.Controller):

    @http.route('/web/dataset/search_read', type='json', auth="user")
    def search_read(self, model, fields=False, offset=0, limit=False, domain=None, sort=None):
        return self.do_search_read(model, fields, offset, limit, domain, sort)

    def do_search_read(self, model, fields=False, offset=0, limit=False, domain=None
                       , sort=None):
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

        records = Model.search_read(domain, fields,
                                    offset=offset or 0, limit=limit or False, order=sort or False)
        if not records:
            return {
                'length': 0,
                'records': []
            }
        if limit and len(records) == limit:
            length = Model.search_count(domain)
        else:
            length = len(records) + (offset or 0)
        return {
            'length': length,
            'records': records
        }

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
    def call_button(self, model, method, args, domain_id=None, context_id=None):
        action = self._call_kw(model, method, args, {})
        if isinstance(action, dict) and action.get('type') != '':
            return clean_action(action)
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

    def placeholder(self, image='placeholder.png'):
        addons_path = http.addons_manifest['web']['addons_path']
        return open(os.path.join(addons_path, 'web', 'static', 'src', 'img', image), 'rb').read()

    def force_contenttype(self, headers, contenttype='image/png'):
        dictheaders = dict(headers)
        dictheaders['Content-Type'] = contenttype
        return list(dictheaders.items())

    @http.route(['/web/content',
        '/web/content/<string:xmlid>',
        '/web/content/<string:xmlid>/<string:filename>',
        '/web/content/<int:id>',
        '/web/content/<int:id>/<string:filename>',
        '/web/content/<int:id>-<string:unique>',
        '/web/content/<int:id>-<string:unique>/<string:filename>',
        '/web/content/<int:id>-<string:unique>/<path:extra>/<string:filename>',
        '/web/content/<string:model>/<int:id>/<string:field>',
        '/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'], type='http', auth="public")
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       filename=None, filename_field='datas_fname', unique=None, mimetype=None,
                       download=None, data=None, token=None, access_token=None, related_id=None, access_mode=None,
                       **kw):
        status, headers, content = binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            access_token=access_token, related_id=related_id, access_mode=access_mode)
        if status == 304:
            response = werkzeug.wrappers.Response(status=status, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200:
            response = request.not_found()
        else:
            content_base64 = base64.b64decode(content)
            headers.append(('Content-Length', len(content_base64)))
            response = request.make_response(content_base64, headers)
        if token:
            response.set_cookie('fileToken', token)
        return response

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
                      filename_field='datas_fname', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, related_id=None, access_mode=None,
                      access_token=None, avoid_if_small=False, upper_limit=False, signature=False, **kw):
        status, headers, content = binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype='image/png', related_id=related_id, access_mode=access_mode, access_token=access_token)
        if status == 304:
            return werkzeug.wrappers.Response(status=304, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200 and download:
            return request.not_found()

        if headers and dict(headers).get('Content-Type', '') == 'image/svg+xml':  # we shan't resize svg images
            height = 0
            width = 0
        else:
            height = int(height or 0)
            width = int(width or 0)

        if not content:
            content = base64.b64encode(self.placeholder(image='placeholder.png'))
            headers = self.force_contenttype(headers, contenttype='image/png')
            if not (width or height):
                suffix = field.split('_')[-1]
                if suffix in ('small', 'medium', 'big'):
                    content = getattr(odoo.tools, 'image_resize_image_%s' % suffix)(content)

        if crop and (width or height):
            content = crop_image(content, type='center', size=(width, height), ratio=(1, 1))
        elif (width or height):
            if not upper_limit:
                # resize maximum 500*500
                if width > 500:
                    width = 500
                if height > 500:
                    height = 500
            content = odoo.tools.image_resize_image(base64_source=content, size=(width or None, height or None),
                                                    encoding='base64', upper_limit=upper_limit,
                                                    avoid_if_small=avoid_if_small)

        image_base64 = base64.b64decode(content)
        headers.append(('Content-Length', len(image_base64)))
        response = request.make_response(image_base64, headers)
        response.status_code = status
        return response

    # backward compatibility
    @http.route(['/web/binary/image'], type='http', auth="public")
    def content_image_backward_compatibility(self, model, id, field, resize=None, **kw):
        width = None
        height = None
        if resize:
            width, height = resize.split(",")
        return self.content_image(model=model, id=id, field=field, width=width, height=height)


    @http.route('/web/binary/upload', type='http', auth="user")
    @serialize_exception
    def upload(self, callback, ufile):
        # TODO: might be useful to have a configuration flag for max-length file uploads
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        try:
            data = ufile.read()
            args = [len(data), ufile.filename,
                    ufile.content_type, base64.b64encode(data)]
        except Exception as e:
            args = [False, str(e)]
        return out % (json.dumps(callback), json.dumps(args))

    @http.route('/web/binary/upload_attachment', type='http', auth="user")
    @serialize_exception
    def upload_attachment(self, callback, model, id, ufile):
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
                    'datas': base64.encodestring(ufile.read()),
                    'datas_fname': filename,
                    'res_model': model,
                    'res_id': int(id)
                })
                attachment._post_add_create()
            except Exception:
                args.append({'error': _("Something horrible happened")})
                _logger.exception("Fail to upload attachment %s" % ufile.filename)
            else:
                args.append({
                    'filename': filename,
                    'mimetype': ufile.content_type,
                    'id': attachment.id
                })
        return out % (json.dumps(callback), json.dumps(args))

    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none", cors="*")
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        placeholder = functools.partial(get_resource_path, 'web', 'static', 'src', 'img')
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

        base_action = Actions.browse([action_id]).read(['type'])
        if base_action:
            ctx = dict(request.context)
            action_type = base_action[0]['type']
            if action_type == 'ir.actions.report':
                ctx.update({'bin_size': True})
            if additional_context:
                ctx.update(additional_context)
            request.context = ctx
            action = request.env[action_type].browse([action_id]).read()
            if action:
                value = clean_action(action[0])
        return value

    @http.route('/web/action/run', type='json', auth="user")
    def run(self, action_id):
        result = request.env['ir.actions.server'].browse([action_id]).run()
        return clean_action(result) if result else False

class Export(http.Controller):

    @http.route('/web/export/formats', type='json', auth="user")
    def formats(self):
        """ Returns all valid export formats

        :returns: for each export format, a pair of identifier and printable name
        :rtype: [(str, str)]
        """
        return [
            {'tag': 'xls', 'label': 'Excel', 'error': None if xlwt else "XLWT 1.3.0 required"},
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

        if import_compat and parent_field_type in ['many2one', 'many2many']:
            fields = self.fields_get(model)
            fields = {k: v for k, v in fields.items() if k in ['id', 'name']}
        else:
            fields = self.fields_get(model)

        if not import_compat:
            fields['.id'] = fields.pop('id', {'string': 'ID'})
        else:
            fields['id']['string'] = _('External ID')

        if parent_field:
            parent_field['string'] = _('External ID')
            fields['id'] = parent_field

        fields_sequence = sorted(fields.items(),
            key=lambda field: (field[0] not in ['id', '.id', 'display_name', 'name'], odoo.tools.ustr(field[1].get('string', ''))))

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
            if field_name == 'name' and import_compat and parent_field_type in ['many2one', 'many2many']:
                # Add name field when expand m2o and m2m fields in import-compatible mode
                id = prefix
            name = parent_name + (parent_name and '/' or '') + field['string']
            record = {'id': id, 'string': name,
                      'value': id, 'children': False,
                      'field_type': field.get('type'),
                      'required': field.get('required'),
                      'relation_field': field.get('relation_field')}
            records.append(record)

            if len(id.split('/')) < 3 and 'relation' in field:
                ref = field.pop('relation')
                if import_compat and field.get('type') in ['many2one', 'many2many']:
                    record['id'] += '/id'
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
    raw_data = False

    @property
    def content_type(self):
        """ Provides the format's content type """
        raise NotImplementedError()

    def filename(self, base):
        """ Creates a valid filename for the format (with extension) from the
         provided base name (exension-less)
        """
        raise NotImplementedError()

    def from_data(self, fields, rows):
        """ Conversion method from Odoo's export data to whatever the
        current export class outputs

        :params list fields: a list of fields to export
        :params list rows: a list of records to export
        :returns:
        :rtype: bytes
        """
        raise NotImplementedError()

    def base(self, data, token):
        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        Model = request.env[model].with_context(import_compat=import_compat, **params.get('context', {}))
        records = Model.browse(ids) or Model.search(domain, offset=0, limit=False, order=False)

        if not Model._is_an_ordinary_table():
            fields = [field for field in fields if field['name'] != 'id']

        field_names = [f['name'] for f in fields]
        import_data = records.export_data(field_names, self.raw_data).get('datas',[])

        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        return request.make_response(self.from_data(columns_headers, import_data),
            headers=[('Content-Disposition',
                            content_disposition(self.filename(model))),
                     ('Content-Type', self.content_type)],
            cookies={'fileToken': token})

class CSVExport(ExportFormat, http.Controller):

    @http.route('/web/export/csv', type='http', auth="user")
    @serialize_exception
    def index(self, data, token):
        return self.base(data, token)

    @property
    def content_type(self):
        return 'text/csv;charset=utf8'

    def filename(self, base):
        return base + '.csv'

    def from_data(self, fields, rows):
        fp = io.BytesIO()
        writer = pycompat.csv_writer(fp, quoting=1)

        writer.writerow(fields)

        for data in rows:
            row = []
            for d in data:
                # Spreadsheet apps tend to detect formulas on leading =, + and -
                if isinstance(d, pycompat.string_types) and d.startswith(('=', '-', '+')):
                    d = "'" + d

                row.append(pycompat.to_text(d))
            writer.writerow(row)

        return fp.getvalue()

class ExcelExport(ExportFormat, http.Controller):
    # Excel needs raw data to correctly handle numbers and date values
    raw_data = True

    @http.route('/web/export/xls', type='http', auth="user")
    @serialize_exception
    def index(self, data, token):
        return self.base(data, token)

    @property
    def content_type(self):
        return 'application/vnd.ms-excel'

    def filename(self, base):
        return base + '.xls'

    def from_data(self, fields, rows):
        if len(rows) > 65535:
            raise UserError(_('There are too many rows (%s rows, limit: 65535) to export as Excel 97-2003 (.xls) format. Consider splitting the export.') % len(rows))

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')

        for i, fieldname in enumerate(fields):
            worksheet.write(0, i, fieldname)
            worksheet.col(i).width = 8000 # around 220 pixels

        base_style = xlwt.easyxf('align: wrap yes')
        date_style = xlwt.easyxf('align: wrap yes', num_format_str='YYYY-MM-DD')
        datetime_style = xlwt.easyxf('align: wrap yes', num_format_str='YYYY-MM-DD HH:mm:SS')

        for row_index, row in enumerate(rows):
            for cell_index, cell_value in enumerate(row):
                cell_style = base_style

                if isinstance(cell_value, bytes) and not isinstance(cell_value, pycompat.string_types):
                    # because xls uses raw export, we can get a bytes object
                    # here. xlwt does not support bytes values in Python 3 ->
                    # assume this is base64 and decode to a string, if this
                    # fails note that you can't export
                    try:
                        cell_value = pycompat.to_text(cell_value)
                    except UnicodeDecodeError:
                        raise UserError(_("Binary fields can not be exported to Excel unless their content is base64-encoded. That does not seem to be the case for %s.") % fields[cell_index])

                if isinstance(cell_value, pycompat.string_types):
                    cell_value = re.sub("\r", " ", pycompat.to_text(cell_value))
                    # Excel supports a maximum of 32767 characters in each cell:
                    cell_value = cell_value[:32767]
                elif isinstance(cell_value, datetime.datetime):
                    cell_style = datetime_style
                elif isinstance(cell_value, datetime.date):
                    cell_style = date_style
                worksheet.write(row_index + 1, cell_index, cell_value, cell_style)

        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

class Apps(http.Controller):
    @http.route('/apps/<app>', auth='user')
    def get_app_url(self, req, app):
        try:
            record = request.env.ref('base.open_module_tree')
            action = record.read(['name', 'type', 'res_model', 'view_mode', 'view_type', 'context', 'views', 'domain'])[0]
            action['target'] = 'current'
        except ValueError:
            action = False
        try:
            app_id = request.env.ref('base.module_%s' % app).id
        except ValueError:
            app_id = False

        if action and app_id:
            action['res_id'] = app_id
            action['view_mode'] = 'form'
            action['views'] = [(False, u'form')]

        sakey = Session().save_session_action(action)
        debug = '?debug' if req.debug else ''
        return werkzeug.utils.redirect('/web{0}#sa={1}'.format(debug, sakey))


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
            # Ignore 'lang' here, because the context in data is the one from the webclient *but* if
            # the user explicitely wants to change the lang, this mechanism overwrites it.
            data['context'] = json.loads(data['context'])
            if data['context'].get('lang'):
                del data['context']['lang']
            context.update(data['context'])
        if converter == 'html':
            html = report.with_context(context).render_qweb_html(docids, data=data)[0]
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = report.with_context(context).render_qweb_pdf(docids, data=data)[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        elif converter == 'text':
            text = report.with_context(context).render_qweb_text(docids, data=data)[0]
            texthttpheaders = [('Content-Type', 'text/plain'), ('Content-Length', len(text))]
            return request.make_response(text, headers=texthttpheaders)
        else:
            raise werkzeug.exceptions.HTTPException(description='Converter %s not implemented.' % converter)

    #------------------------------------------------------
    # Misc. route utils
    #------------------------------------------------------
    @http.route(['/report/barcode', '/report/barcode/<type>/<path:value>'], type='http', auth="public")
    def report_barcode(self, type, value, width=600, height=100, humanreadable=0):
        """Contoller able to render barcode images thanks to reportlab.
        Samples:
            <img t-att-src="'/report/barcode/QR/%s' % o.name"/>
            <img t-att-src="'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s' %
                ('QR', o.name, 200, 200)"/>

        :param type: Accepted types: 'Codabar', 'Code11', 'Code128', 'EAN13', 'EAN8', 'Extended39',
        'Extended93', 'FIM', 'I2of5', 'MSI', 'POSTNET', 'QR', 'Standard39', 'Standard93',
        'UPCA', 'USPS_4State'
        :param humanreadable: Accepted values: 0 (default) or 1. 1 will insert the readable value
        at the bottom of the output image
        """
        try:
            barcode = request.env['ir.actions.report'].barcode(type, value, width=width, height=height, humanreadable=humanreadable)
        except (ValueError, AttributeError):
            raise werkzeug.exceptions.HTTPException(description='Cannot convert into barcode.')

        return request.make_response(barcode, headers=[('Content-Type', 'image/png')])

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token):
        """This function is used by 'action_manager_report.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = json.loads(data)
        url, type = requestcontent[0], requestcontent[1]
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
                    response = self.report_routes(reportname, docids=docids, converter=converter)
                else:
                    # Particular report:
                    data = url_decode(url.split('?')[1]).items()  # decoding the args represented in JSON
                    response = self.report_routes(reportname, converter=converter, **dict(data))

                report = request.env['ir.actions.report']._get_report_from_name(reportname)
                filename = "%s.%s" % (report.name, extension)

                if docids:
                    ids = [int(x) for x in docids.split(",")]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                response.headers.add('Content-Disposition', content_disposition(filename))
                response.set_cookie('fileToken', token)
                return response
            else:
                return
        except Exception as e:
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
