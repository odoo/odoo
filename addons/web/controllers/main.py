# -*- coding: utf-8 -*-

import base64
import csv
import functools
import glob
import imghdr
import itertools
import jinja2
import logging
import operator
import datetime
import hashlib
import os
import re
import json
import sys
import time
import zlib
from xml.etree import ElementTree
from cStringIO import StringIO

import babel.messages.pofile
import werkzeug.utils
import werkzeug.wrappers
from openerp.api import Environment

import openerp
import openerp.modules.registry
from openerp.addons.base.ir.ir_qweb import AssetsBundle, QWebTemplateNotFound
from openerp.modules import get_resource_path
from openerp.tools import topological_sort
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.tools.misc import str2bool, xlwt
from openerp import http
from openerp.http import request, serialize_exception as _serialize_exception, content_disposition
from openerp.exceptions import AccessError

_logger = logging.getLogger(__name__)

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('openerp.addons.web', "views")

env = jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps

# 1 week cache for asset bundles as advised by Google Page Speed
BUNDLE_MAXAGE = 60 * 60 * 24 * 7

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

#----------------------------------------------------------
# OpenERP Web helpers
#----------------------------------------------------------

db_list = http.db_list

db_monodb = http.db_monodb

def serialize_exception(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception, e:
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
        url_redirect = r.base_url
        if r.query_string:
            # Can't use werkzeug.wrappers.BaseRequest.url with encoded hashes:
            # https://github.com/amigrave/werkzeug/commit/b4a62433f2f7678c234cdcac6247a869f90a7eb7
            url_redirect += '?' + r.query_string
        response = werkzeug.utils.redirect(url_redirect, 302)
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
    loadable = http.addons_manifest.keys()

    # Retrieve database installed modules
    # TODO The following code should move to ir.module.module.list_installed_modules()
    Modules = environment['ir.module.module']
    domain = [('state','=','installed'), ('name','in', loadable)]
    modules = {
        module.name: module.dependencies_id.mapped('name')
        for module in Modules.search(domain)
    }

    sorted_modules = topological_sort(modules)
    return sorted_modules

def module_installed_bypass_session(dbname):
    try:
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            return module_installed(
                environment=Environment(cr, openerp.SUPERUSER_ID, {}))
    except Exception:
        pass
    return {}

def module_boot(db=None):
    server_wide_modules = openerp.conf.server_wide_modules or ['web']
    serverside = []
    dbside = []
    for i in server_wide_modules:
        if i in http.addons_manifest:
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
    :rtype: (str, str)
    """
    checksum = hashlib.new('sha1')
    if not file_list:
        return '', checksum.hexdigest()

    root = None
    for fname in file_list:
        with open(fname, 'rb') as fp:
            contents = fp.read()
            checksum.update(contents)
            fp.seek(0)
            xml = ElementTree.parse(fp).getroot()

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
        _logger.warning("openerp.addons.web.main.manifest_list(): debug parameter is deprecated")
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

def load_actions_from_ir_values(action_slot, model, res_id):
    ir_values = request.session.model('ir.values')
    actions = ir_values.get_actions(action_slot=action_slot, model=model, res_id=res_id, context=request.context)
    return [(id, name, clean_action(action)) for id, name, action in actions]

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
    """ For historical reasons, OpenERP has weird dealings in relation to
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

def binary_content(xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream', env=None):
    return request.registry['ir.http'].binary_content(
        xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field,
        download=download, mimetype=mimetype, default_mimetype=default_mimetype, env=env)

#----------------------------------------------------------
# OpenERP Web web Controllers
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
        menu_data = request.registry['ir.ui.menu'].load_menus(request.cr, request.uid, request.debug, context=request.context)

        version_info = openerp.service.common.exp_version()
        db_info = {
            'server_version': version_info.get('server_version'),
            'server_version_info': version_info.get('server_version_info'),
        }

        return request.render('web.webclient_bootstrap', qcontext={'menu_data': menu_data, 'db_info': json.dumps(db_info)})

    @http.route('/web/dbredirect', type='http', auth="none")
    def web_db_redirect(self, redirect='/', **kw):
        ensure_db()
        return werkzeug.utils.redirect(redirect, 303)

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = openerp.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except openerp.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid is not False:
                request.params['login_success'] = True
                if not redirect:
                    redirect = '/web'
                return http.redirect_with_hash(redirect)
            request.uid = old_uid
            values['error'] = _("Wrong login/password")
        return request.render('web.login', values)

class WebClient(http.Controller):

    @http.route('/web/webclient/csslist', type='json', auth="none")
    def csslist(self, mods=None):
        return manifest_list('css', mods=mods)

    @http.route('/web/webclient/jslist', type='json', auth="none")
    def jslist(self, mods=None):
        return manifest_list('js', mods=mods)

    @http.route('/web/webclient/locale/<string:lang>', type='http', auth="none")
    def load_locale(self, lang):
        magic_file_finding = [lang.replace("_",'-').lower(), lang.split('_')[0]]
        addons_path = http.addons_manifest['web']['addons_path']
        #load momentjs locale
        momentjs_locale_file = False
        momentjs_locale = ""
        for code in magic_file_finding:
            try:
                with open(os.path.join(addons_path, 'web', 'static', 'lib', 'moment', 'locale', code + '.js'), 'r') as f:
                    momentjs_locale = f.read()
                #we found a locale matching so we can exit
                break
            except IOError:
                continue

        #return the content of the locale
        headers = [('Content-Type', 'application/javascript'), ('Cache-Control', 'max-age=%s' % (36000))]
        return request.make_response(momentjs_locale, headers)

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
        uid = openerp.SUPERUSER_ID
        if mods is None:
            m = request.registry.get('ir.module.module')
            mods = [x['name'] for x in m.search_read(request.cr, uid,
                [('state','=','installed')], ['name'])]
        if lang is None:
            lang = request.context["lang"]
        res_lang = request.registry.get('res.lang')
        ids = res_lang.search(request.cr, uid, [("code", "=", lang)])
        lang_params = None
        if ids:
            lang_params = res_lang.read(request.cr, uid, ids[0],
                ["name", "direction", "date_format", "time_format", "grouping", "decimal_point", "thousands_sep"])

        # Regional languages (ll_CC) must inherit/override their parent lang (ll), but this is
        # done server-side when the language is loaded, so we only need to load the user's lang.
        ir_translation = request.registry.get('ir.translation')
        translations_per_module = {}
        messages = ir_translation.search_read(request.cr, uid, [('module','in',mods),('lang','=',lang),
                                               ('comments','like','openerp-web'),('value','!=',False),
                                               ('value','!=','')],
                                              ['module','src','value','lang'], order='module')
        for mod, msg_group in itertools.groupby(messages, key=operator.itemgetter('module')):
            translations_per_module.setdefault(mod,{'messages':[]})
            translations_per_module[mod]['messages'].extend({'id': m['src'],
                                                             'string': m['value']} \
                                                                for m in msg_group)
        return {
            'lang_parameters': lang_params,
            'modules': translations_per_module,
            'multi_lang': len(res_lang.get_installed(request.cr, uid)) > 1,
        }

    @http.route('/web/webclient/version_info', type='json', auth="none")
    def version_info(self):
        return openerp.service.common.exp_version()

    @http.route('/web/tests', type='http', auth="none")
    def index(self, mod=None, **kwargs):
        return request.render('web.qunit_suite')

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
            client = Client(request.httprequest.app, BaseResponse)
            headers = {'X-Openerp-Session-Id': request.session.sid}
            return client.post('/' + path, base_url=base_url, query_string=query_string,
                               headers=headers, data=data)

class Database(http.Controller):

    def _render_template(self, **d):
        d.setdefault('manage',True)
        d['insecure'] = openerp.tools.config['admin_passwd'] == 'admin'
        d['list_db'] = openerp.tools.config['list_db']
        d['langs'] = openerp.service.db.exp_list_lang()
        d['countries'] = openerp.service.db.exp_list_countries()
        d['pattern'] = DBNAME_PATTERN
        # databases list
        d['databases'] = []
        try:
            d['databases'] = http.db_list()
        except openerp.exceptions.AccessDenied:
            monodb = db_monodb()
            if monodb:
                d['databases'] = [monodb]
        return env.get_template("database_manager.html").render(d)

    @http.route('/web/database/selector', type='http', auth="none")
    def selector(self, **kw):
        return self._render_template(manage=False)

    @http.route('/web/database/manager', type='http', auth="none")
    def manager(self, **kw):
        return self._render_template()

    @http.route('/web/database/create', type='http', auth="none", methods=['POST'], csrf=False)
    def create(self, master_pwd, name, lang, password, **post):
        try:
            if not re.match(DBNAME_PATTERN, name):
                raise Exception(_('Invalid database name. Only alphanumerical characters, underscore, hyphen and dot are allowed.'))
            # country code could be = "False" which is actually True in python
            country_code = post.get('country_code') or False
            request.session.proxy("db").create_database(master_pwd, name, bool(post.get('demo')), lang, password, post['login'], country_code)
            request.session.authenticate(name, post['login'], password)
            return http.local_redirect('/web/')
        except Exception, e:
            error = "Database creation error: %s" % e
        return self._render_template(error=error)

    @http.route('/web/database/duplicate', type='http', auth="none", methods=['POST'], csrf=False)
    def duplicate(self, master_pwd, name, new_name):
        try:
            if not re.match(DBNAME_PATTERN, new_name):
                raise Exception(_('Invalid database name. Only alphanumerical characters, underscore, hyphen and dot are allowed.'))
            request.session.proxy("db").duplicate_database(master_pwd, name, new_name)
            return http.local_redirect('/web/database/manager')
        except Exception, e:
            error = "Database duplication error: %s" % e
            return self._render_template(error=error)

    @http.route('/web/database/drop', type='http', auth="none", methods=['POST'], csrf=False)
    def drop(self, master_pwd, name):
        try:
            request.session.proxy("db").drop(master_pwd, name)
            return http.local_redirect('/web/database/manager')
        except Exception, e:
            error = "Database deletion error: %s" % e
            return self._render_template(error=error)

    @http.route('/web/database/backup', type='http', auth="none", methods=['POST'], csrf=False)
    def backup(self, master_pwd, name, backup_format = 'zip'):
        try:
            openerp.service.db.check_super(master_pwd)
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            filename = "%s_%s.%s" % (name, ts, backup_format)
            headers = [
                ('Content-Type', 'application/octet-stream; charset=binary'),
                ('Content-Disposition', content_disposition(filename)),
            ]
            dump_stream = openerp.service.db.dump_db(name, None, backup_format)
            response = werkzeug.wrappers.Response(dump_stream, headers=headers, direct_passthrough=True)
            return response
        except Exception, e:
            _logger.exception('Database.backup')
            error = "Database backup error: %s" % e
            return self._render_template(error=error)

    @http.route('/web/database/restore', type='http', auth="none", methods=['POST'], csrf=False)
    def restore(self, master_pwd, backup_file, name, copy=False):
        try:
            data = base64.b64encode(backup_file.read())
            request.session.proxy("db").restore(master_pwd, name, data, str2bool(copy))
            return http.local_redirect('/web/database/manager')
        except Exception, e:
            error = "Database restore error: %s" % e
            return self._render_template(error=error)

    @http.route('/web/database/change_password', type='http', auth="none", methods=['POST'], csrf=False)
    def change_password(self, master_pwd, master_pwd_new):
        try:
            request.session.proxy("db").change_admin_password(master_pwd, master_pwd_new)
            return http.local_redirect('/web/database/manager')
        except Exception, e:
            error = "Master password update error: %s" % e
            return self._render_template(error=error)

class Session(http.Controller):

    def session_info(self):
        request.session.ensure_valid()
        user = request.env.user
        display_switch_company_menu = user.has_group('base.group_multi_company') and len(user.company_ids) > 1
        return {
            "session_id": request.session_id,
            "uid": request.session.uid,
            "user_context": request.session.get_context() if request.session.uid else {},
            "db": request.session.db,
            "username": request.session.login,
            "company_id": request.env.user.company_id.id if request.session.uid else None,
            "partner_id": request.env.user.partner_id.id if request.session.uid and request.env.user.partner_id else None,
            "user_companies": {'current_company': (user.company_id.id, user.company_id.name), 'allowed_companies': [(comp.id, comp.name) for comp in user.company_ids]} if display_switch_company_menu else False,
        }

    @http.route('/web/session/get_session_info', type='json', auth="none")
    def get_session_info(self):
        request.uid = request.session.uid
        request.disable_db = False
        return self.session_info()

    @http.route('/web/session/authenticate', type='json', auth="none")
    def authenticate(self, db, login, password, base_location=None):
        request.session.authenticate(db, login, password)

        return self.session_info()

    @http.route('/web/session/change_password', type='json', auth="user")
    def change_password(self, fields):
        old_password, new_password,confirm_password = operator.itemgetter('old_pwd', 'new_password','confirm_pwd')(
                dict(map(operator.itemgetter('name', 'value'), fields)))
        if not (old_password.strip() and new_password.strip() and confirm_password.strip()):
            return {'error':_('You cannot leave any password empty.'),'title': _('Change Password')}
        if new_password != confirm_password:
            return {'error': _('The new password and its confirmation must be identical.'),'title': _('Change Password')}
        try:
            if request.session.model('res.users').change_password(
                old_password, new_password):
                return {'new_password':new_password}
        except Exception:
            return {'error': _('The old password you provided is incorrect, your password was not changed.'), 'title': _('Change Password')}
        return {'error': _('Error, password not changed !'), 'title': _('Change Password')}

    @http.route('/web/session/get_lang_list', type='json', auth="none")
    def get_lang_list(self):
        try:
            return request.session.proxy("db").list_lang() or []
        except Exception, e:
            return {"error": e, "title": _("Languages")}

    @http.route('/web/session/modules', type='json', auth="user")
    def modules(self):
        # return all installed modules. Web client is smart enough to not load a module twice
        return module_installed(environment=request.env(user=openerp.SUPERUSER_ID))

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
        return request.httpsession.save_action(the_action)

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
        return request.httpsession.get_action(key)

    @http.route('/web/session/check', type='json', auth="user")
    def check(self):
        request.session.assert_valid()
        return None

    @http.route('/web/session/destroy', type='json', auth="user")
    def destroy(self):
        request.session.logout()

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)

class Menu(http.Controller):

    @http.route('/web/menu/load_needaction', type='json', auth="user")
    def load_needaction(self, menu_ids):
        """ Loads needaction counters for specific menu ids.

            :return: needaction data
            :rtype: dict(menu_id: {'needaction_enabled': boolean, 'needaction_counter': int})
        """
        return request.session.model('ir.ui.menu').get_needaction_data(menu_ids, request.context)

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
        Model = request.session.model(model)

        records = Model.search_read(domain, fields, offset or 0, limit or False, sort or False,
                           request.context)
        if not records:
            return {
                'length': 0,
                'records': []
            }
        if limit and len(records) == limit:
            length = Model.search_count(domain, request.context)
        else:
            length = len(records) + (offset or 0)
        return {
            'length': length,
            'records': records
        }

    @http.route('/web/dataset/load', type='json', auth="user")
    def load(self, model, id, fields):
        m = request.session.model(model)
        value = {}
        r = m.read([id], False, request.context)
        if r:
            value = r[0]
        return {'value': value}

    def call_common(self, model, method, args, domain_id=None, context_id=None):
        return self._call_kw(model, method, args, {})

    def _call_kw(self, model, method, args, kwargs):
        if method.startswith('_'):
            raise AccessError(_("Underscore prefixed methods cannot be remotely called"))

        return getattr(request.registry.get(model), method)(request.cr, request.uid, *args, **kwargs)

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

    @http.route('/web/dataset/exec_workflow', type='json', auth="user")
    def exec_workflow(self, model, id, signal):
        return request.session.exec_workflow(model, id, signal)

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
        m = request.session.model(model)
        if not m.fields_get([field]):
            return False
        # python 2.6 has no start parameter
        for i, id in enumerate(ids):
            m.write(id, { field: i + offset })
        return True

class View(http.Controller):

    @http.route('/web/view/add_custom', type='json', auth="user")
    def add_custom(self, view_id, arch):
        CustomView = request.session.model('ir.ui.view.custom')
        CustomView.create({
            'user_id': request.session.uid,
            'ref_id': view_id,
            'arch': arch
        }, request.context)
        return {'result': True}

class TreeView(View):

    @http.route('/web/treeview/action', type='json', auth="user")
    def action(self, model, id):
        return load_actions_from_ir_values('tree_but_open', model, id)

class Binary(http.Controller):

    def placeholder(self, image='placeholder.png'):
        addons_path = http.addons_manifest['web']['addons_path']
        return open(os.path.join(addons_path, 'web', 'static', 'src', 'img', image), 'rb').read()

    def force_contenttype(self, headers, contenttype='image/png'):
        dictheaders = dict(headers)
        dictheaders['Content-Type'] = contenttype
        return dictheaders.items()

    @http.route(['/web/content',
        '/web/content/<string:xmlid>',
        '/web/content/<string:xmlid>/<string:filename>',
        '/web/content/<int:id>',
        '/web/content/<int:id>/<string:filename>',
        '/web/content/<int:id>-<string:unique>',
        '/web/content/<int:id>-<string:unique>/<string:filename>',
        '/web/content/<string:model>/<int:id>/<string:field>',
        '/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'], type='http', auth="public")
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='datas', filename=None, filename_field='datas_fname', unique=None, mimetype=None, download=None, data=None, token=None):
        status, headers, content = binary_content(xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field, download=download, mimetype=mimetype)
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
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas', filename_field='datas_fname', unique=None, filename=None, mimetype=None, download=None, width=0, height=0):
        status, headers, content = binary_content(xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field, download=download, mimetype=mimetype, default_mimetype='image/png')
        if status == 304:
            return werkzeug.wrappers.Response(status=304, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200 and download:
            return request.not_found()

        if content and (width or height):
            # resize maximum 500*500
            if width > 500:
                width = 500
            if height > 500:
                height = 500
            content = openerp.tools.image_resize_image(base64_source=content, size=(width or None, height or None), encoding='base64', filetype='PNG')
            # resize force png as filetype
            headers = self.force_contenttype(headers, contenttype='image/png')

        if content:
            image_base64 = base64.b64decode(content)
        else:
            image_base64 = self.placeholder(image='placeholder.png')  # could return (contenttype, content) in master
            headers = self.force_contenttype(headers, contenttype='image/png')

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
        except Exception, e:
            args = [False, e.message]
        return out % (json.dumps(callback), json.dumps(args))

    @http.route('/web/binary/upload_attachment', type='http', auth="user")
    @serialize_exception
    def upload_attachment(self, callback, model, id, ufile):
        Model = request.session.model('ir.attachment')
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        try:
            attachment_id = Model.create({
                'name': ufile.filename,
                'datas': base64.encodestring(ufile.read()),
                'datas_fname': ufile.filename,
                'res_model': model,
                'res_id': int(id)
            }, request.context)
            args = {
                'filename': ufile.filename,
                'mimetype': ufile.content_type,
                'id':  attachment_id
            }
        except Exception:
            args = {'error': _("Something horrible happened")}
            _logger.exception("Fail to upload attachment %s" % ufile.filename)
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
            uid = openerp.SUPERUSER_ID

        if not dbname:
            response = http.send_file(placeholder(imgname + imgext))
        else:
            try:
                # create an empty registry
                registry = openerp.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    cr.execute("""SELECT c.logo_web, c.write_date
                                    FROM res_users u
                               LEFT JOIN res_company c
                                      ON c.id = u.company_id
                                   WHERE u.id = %s
                               """, (uid,))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_base64 = str(row[0]).decode('base64')
                        image_data = StringIO(image_base64)
                        imgext = '.' + (imghdr.what(None, h=image_base64) or 'png')
                        response = http.send_file(image_data, filename=imgname + imgext, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname + imgext))

        return response

class Action(http.Controller):

    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        Actions = request.session.model('ir.actions.actions')
        value = False
        try:
            action_id = int(action_id)
        except ValueError:
            try:
                module, xmlid = action_id.split('.', 1)
                model, action_id = request.session.model('ir.model.data').get_object_reference(module, xmlid)
                assert model.startswith('ir.actions.')
            except Exception:
                action_id = 0   # force failed read

        base_action = Actions.read([action_id], ['type'], request.context)
        if base_action:
            ctx = request.context
            action_type = base_action[0]['type']
            if action_type == 'ir.actions.report.xml':
                ctx.update({'bin_size': True})
            if additional_context:
                ctx.update(additional_context)
            action = request.session.model(action_type).read([action_id], False, ctx)
            if action:
                value = clean_action(action[0])
        return value

    @http.route('/web/action/run', type='json', auth="user")
    def run(self, action_id):
        return_action = request.session.model('ir.actions.server').run(
            [action_id], request.context)
        if return_action:
            return clean_action(return_action)
        else:
            return False

class Export(http.Controller):

    @http.route('/web/export/formats', type='json', auth="user")
    def formats(self):
        """ Returns all valid export formats

        :returns: for each export format, a pair of identifier and printable name
        :rtype: [(str, str)]
        """
        return [
            {'tag': 'csv', 'label': 'CSV'},
            {'tag': 'xls', 'label': 'Excel', 'error': None if xlwt else "XLWT required"},
        ]

    def fields_get(self, model):
        Model = request.session.model(model)
        fields = Model.fields_get(False, request.context)
        return fields

    @http.route('/web/export/get_fields', type='json', auth="user")
    def get_fields(self, model, prefix='', parent_name= '',
                   import_compat=True, parent_field_type=None,
                   exclude=None):

        if import_compat and parent_field_type == "many2one":
            fields = {}
        else:
            fields = self.fields_get(model)

        if import_compat:
            fields.pop('id', None)
        else:
            fields['.id'] = fields.pop('id', {'string': 'ID'})

        fields_sequence = sorted(fields.iteritems(),
            key=lambda field: openerp.tools.ustr(field[1].get('string', '')))

        records = []
        for field_name, field in fields_sequence:
            if import_compat:
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
            name = parent_name + (parent_name and '/' or '') + field['string']
            record = {'id': id, 'string': name,
                      'value': id, 'children': False,
                      'field_type': field.get('type'),
                      'required': field.get('required'),
                      'relation_field': field.get('relation_field')}
            records.append(record)

            if len(name.split('/')) < 3 and 'relation' in field:
                ref = field.pop('relation')
                record['value'] += '/id'
                record['params'] = {'model': ref, 'prefix': id, 'name': name}

                if not import_compat or field['type'] == 'one2many':
                    # m2m field in import_compat is childless
                    record['children'] = True

        return records

    @http.route('/web/export/namelist', type='json', auth="user")
    def namelist(self, model, export_id):
        # TODO: namelist really has no reason to be in Python (although itertools.groupby helps)
        export = request.session.model("ir.exports").read([export_id])[0]
        export_fields_list = request.session.model("ir.exports.line").read(
            export['export_fields'])

        fields_data = self.fields_info(
            model, map(operator.itemgetter('name'), export_fields_list))

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
            for k, v in self.fields_info(model, export_fields).iteritems())

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
        """ Conversion method from OpenERP's export data to whatever the
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
            operator.itemgetter('model', 'fields', 'ids', 'domain',
                                'import_compat')(
                params)

        Model = request.session.model(model)
        context = dict(request.context or {}, **params.get('context', {}))
        ids = ids or Model.search(domain, offset=0, limit=False, order=False, context=context)

        if not request.env[model]._is_an_ordinary_table():
            fields = [field for field in fields if field['name'] != 'id']

        field_names = map(operator.itemgetter('name'), fields)
        import_data = Model.export_data(ids, field_names, self.raw_data, context=context).get('datas',[])

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
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        writer.writerow([name.encode('utf-8') for name in fields])

        for data in rows:
            row = []
            for d in data:
                if isinstance(d, unicode):
                    try:
                        d = d.encode('utf-8')
                    except UnicodeError:
                        pass
                if d is False: d = None

                # Spreadsheet apps tend to detect formulas on leading =, + and -
                if type(d) is str and d.startswith(('=', '-', '+')):
                    d = "'" + d

                row.append(d)
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

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
                if isinstance(cell_value, basestring):
                    cell_value = re.sub("\r", " ", cell_value)
                elif isinstance(cell_value, datetime.datetime):
                    cell_style = datetime_style
                elif isinstance(cell_value, datetime.date):
                    cell_style = date_style
                worksheet.write(row_index + 1, cell_index, cell_value, cell_style)

        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

class Reports(http.Controller):
    POLLING_DELAY = 0.25
    TYPES_MAPPING = {
        'doc': 'application/vnd.ms-word',
        'html': 'text/html',
        'odt': 'application/vnd.oasis.opendocument.text',
        'pdf': 'application/pdf',
        'sxw': 'application/vnd.sun.xml.writer',
        'xls': 'application/vnd.ms-excel',
    }

    @http.route('/web/report', type='http', auth="user")
    @serialize_exception
    def index(self, action, token):
        action = json.loads(action)

        report_srv = request.session.proxy("report")
        context = dict(request.context)
        context.update(action["context"])

        report_data = {}
        report_ids = context.get("active_ids", None)
        if 'report_type' in action:
            report_data['report_type'] = action['report_type']
        if 'datas' in action:
            if 'ids' in action['datas']:
                report_ids = action['datas'].pop('ids')
            report_data.update(action['datas'])

        report_id = report_srv.report(
            request.session.db, request.session.uid, request.session.password,
            action["report_name"], report_ids,
            report_data, context)

        report_struct = None
        while True:
            report_struct = report_srv.report_get(
                request.session.db, request.session.uid, request.session.password, report_id)
            if report_struct["state"]:
                break

            time.sleep(self.POLLING_DELAY)

        report = base64.b64decode(report_struct['result'])
        if report_struct.get('code') == 'zlib':
            report = zlib.decompress(report)
        report_mimetype = self.TYPES_MAPPING.get(
            report_struct['format'], 'octet-stream')
        file_name = action.get('name', 'report')
        if 'name' not in action:
            reports = request.session.model('ir.actions.report.xml')
            res_id = reports.search([('report_name', '=', action['report_name']),],
                                    context=context)
            if len(res_id) > 0:
                file_name = reports.read(res_id[0], ['name'], context)['name']
            else:
                file_name = action['report_name']
        file_name = '%s.%s' % (file_name, report_struct['format'])

        return request.make_response(report,
             headers=[
                 ('Content-Disposition', content_disposition(file_name)),
                 ('Content-Type', report_mimetype),
                 ('Content-Length', len(report))],
             cookies={'fileToken': token})

class Apps(http.Controller):
    @http.route('/apps/<app>', auth='user')
    def get_app_url(self, req, app):
        act_window_obj = request.session.model('ir.actions.act_window')
        ir_model_data = request.session.model('ir.model.data')
        try:
            action_id = ir_model_data.get_object_reference('base', 'open_module_tree')[1]
            action = act_window_obj.read(action_id, ['name', 'type', 'res_model', 'view_mode', 'view_type', 'context', 'views', 'domain'])
            action['target'] = 'current'
        except ValueError:
            action = False
        try:
            app_id = ir_model_data.get_object_reference('base', 'module_%s' % app)[1]
        except ValueError:
            app_id = False

        if action and app_id:
            action['res_id'] = app_id
            action['view_mode'] = 'form'
            action['views'] = [(False, u'form')]

        sakey = Session().save_session_action(action)
        debug = '?debug' if req.debug else ''
        return werkzeug.utils.redirect('/web{0}#sa={1}'.format(debug, sakey))
