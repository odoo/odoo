# -*- coding: utf-8 -*-

import ast
import base64
import csv
import glob
import itertools
import logging
import operator
import datetime
import hashlib
import os
import re
import simplejson
import time
import urllib2
import xmlrpclib
import zlib
from xml.etree import ElementTree
from cStringIO import StringIO

import babel.messages.pofile
import werkzeug.utils
import werkzeug.wrappers
try:
    import xlwt
except ImportError:
    xlwt = None

from .. import common
openerpweb = common.http

#----------------------------------------------------------
# OpenERP Web web Controllers
#----------------------------------------------------------


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


def concat_files(file_list, reader=None, intersperse=""):
    """ Concatenates contents of all provided files

    :param list(str) file_list: list of files to check
    :param function reader: reading procedure for each file
    :param str intersperse: string to intersperse between file contents
    :returns: (concatenation_result, checksum)
    :rtype: (str, str)
    """
    checksum = hashlib.new('sha1')
    if not file_list:
        return '', checksum.hexdigest()

    if reader is None:
        def reader(f):
            with open(f, 'rb') as fp:
                return fp.read()

    files_content = []
    for fname in file_list:
        contents = reader(fname)
        checksum.update(contents)
        files_content.append(contents)

    files_concat = intersperse.join(files_content)
    return files_concat, checksum.hexdigest()

html_template = """<!DOCTYPE html>
<html style="height: 100%%">
    <head>
        <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>
        <meta http-equiv="content-type" content="text/html; charset=utf-8" />
        <title>OpenERP</title>
        <link rel="shortcut icon" href="/web/static/src/img/favicon.ico" type="image/x-icon"/>
        <link rel="stylesheet" href="/web/static/src/css/full.css" />
        %(css)s
        %(js)s
        <script type="text/javascript">
            $(function() {
                var s = new openerp.init(%(modules)s);
                %(init)s
            });
        </script>
    </head>
    <body></body>
</html>
"""

def sass2scss(src):
    # Validated by diff -u of sass2scss against:
    # sass-convert -F sass -T scss openerp.sass openerp.scss
    block = []
    sass = ('', block)
    reComment = re.compile(r'//.*$')
    reIndent = re.compile(r'^\s+')
    reIgnore = re.compile(r'^\s*(//.*)?$')
    reFixes = { re.compile(r'\(\((.*)\)\)') : r'(\1)', }
    lastLevel = 0
    prevBlocks = {}
    for l in src.split('\n'):
        l = l.rstrip()
        if reIgnore.search(l): continue
        l = reComment.sub('', l)
        l = l.rstrip()
        indent = reIndent.match(l)
        level = indent.end() if indent else 0
        l = l[level:]
        if level>lastLevel:
            prevBlocks[lastLevel] = block
            newBlock = []
            block[-1] = (block[-1], newBlock)
            block = newBlock
        elif level<lastLevel:
            block = prevBlocks[level]
        lastLevel = level
        if not l: continue
        # Fixes
        for ereg, repl in reFixes.items():
            l = ereg.sub(repl if type(repl)==str else repl(), l)
        block.append(l)

    def write(sass, level=-1):
        out = ""
        indent = '  '*level
        if type(sass)==tuple:
            if level>=0:
                out += indent+sass[0]+" {\n"
            for e in sass[1]:
                out += write(e, level+1)
            if level>=0:
                out = out.rstrip(" \n")
                out += ' }\n'
            if level==0:
                out += "\n"
        else:
            out += indent+sass+";\n"
        return out
    return write(sass)

class WebClient(openerpweb.Controller):
    _cp_path = "/web/webclient"

    def server_wide_modules(self, req):
        addons = [i for i in req.config.server_wide_modules if i in openerpweb.addons_manifest]
        return addons

    def manifest_glob(self, req, addons, key):
        if addons is None:
            addons = self.server_wide_modules(req)
        else:
            addons = addons.split(',')
        r = []
        for addon in addons:
            manifest = openerpweb.addons_manifest.get(addon, None)
            if not manifest:
                continue
            # ensure does not ends with /
            addons_path = os.path.join(manifest['addons_path'], '')[:-1]
            globlist = manifest.get(key, [])
            for pattern in globlist:
                for path in glob.glob(os.path.normpath(os.path.join(addons_path, addon, pattern))):
                    r.append( (path, path[len(addons_path):]))
        return r

    def manifest_list(self, req, mods, extension):
        if not req.debug:
            path = '/web/webclient/' + extension
            if mods is not None:
                path += '?mods=' + mods
            return [path]
        # old code to force cache reloading
        #return ['%s?debug=%s' % (wp, os.path.getmtime(fp)) for fp, wp in self.manifest_glob(req, mods, extension)]
        return [el[1] for el in self.manifest_glob(req, mods, extension)]

    @openerpweb.jsonrequest
    def csslist(self, req, mods=None):
        return self.manifest_list(req, mods, 'css')

    @openerpweb.jsonrequest
    def jslist(self, req, mods=None):
        return self.manifest_list(req, mods, 'js')

    @openerpweb.jsonrequest
    def qweblist(self, req, mods=None):
        return self.manifest_list(req, mods, 'qweb')

    def get_last_modified(self, files):
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

    def make_conditional(self, req, response, last_modified=None, etag=None):
        """ Makes the provided response conditional based upon the request,
        and mandates revalidation from clients

        Uses Werkzeug's own :meth:`ETagResponseMixin.make_conditional`, after
        setting ``last_modified`` and ``etag`` correctly on the response object

        :param req: OpenERP request
        :type req: web.common.http.WebRequest
        :param response: Werkzeug response
        :type response: werkzeug.wrappers.Response
        :param datetime.datetime last_modified: last modification date of the response content
        :param str etag: some sort of checksum of the content (deep etag)
        :return: the response object provided
        :rtype: werkzeug.wrappers.Response
        """
        response.cache_control.must_revalidate = True
        response.cache_control.max_age = 0
        if last_modified:
            response.last_modified = last_modified
        if etag:
            response.set_etag(etag)
        return response.make_conditional(req.httprequest)

    @openerpweb.httprequest
    def css(self, req, mods=None):
        files = list(self.manifest_glob(req, mods, 'css'))
        last_modified = self.get_last_modified(f[0] for f in files)
        if req.httprequest.if_modified_since and req.httprequest.if_modified_since >= last_modified:
            return werkzeug.wrappers.Response(status=304)

        file_map = dict(files)

        rx_import = re.compile(r"""@import\s+('|")(?!'|"|/|https?://)""", re.U)
        rx_url = re.compile(r"""url\s*\(\s*('|"|)(?!'|"|/|https?://)""", re.U)


        def reader(f):
            """read the a css file and absolutify all relative uris"""
            with open(f, 'rb') as fp:
                data = fp.read().decode('utf-8')

            path = file_map[f]
            # convert FS path into web path
            web_dir = '/'.join(os.path.dirname(path).split(os.path.sep))

            data = re.sub(
                rx_import,
                r"""@import \1%s/""" % (web_dir,),
                data,
            )

            data = re.sub(
                rx_url,
                r"""url(\1%s/""" % (web_dir,),
                data,
            )
            return data.encode('utf-8')

        content, checksum = concat_files((f[0] for f in files), reader)

        return self.make_conditional(
            req, req.make_response(content, [('Content-Type', 'text/css')]),
            last_modified, checksum)

    @openerpweb.httprequest
    def js(self, req, mods=None):
        files = [f[0] for f in self.manifest_glob(req, mods, 'js')]
        last_modified = self.get_last_modified(files)
        if req.httprequest.if_modified_since and req.httprequest.if_modified_since >= last_modified:
            return werkzeug.wrappers.Response(status=304)

        content, checksum = concat_files(files, intersperse=';')

        return self.make_conditional(
            req, req.make_response(content, [('Content-Type', 'application/javascript')]),
            last_modified, checksum)

    @openerpweb.httprequest
    def qweb(self, req, mods=None):
        files = [f[0] for f in self.manifest_glob(req, mods, 'qweb')]
        last_modified = self.get_last_modified(files)
        if req.httprequest.if_modified_since and req.httprequest.if_modified_since >= last_modified:
            return werkzeug.wrappers.Response(status=304)

        content,checksum = concat_xml(files)

        return self.make_conditional(
            req, req.make_response(content, [('Content-Type', 'text/xml')]),
            last_modified, checksum)

    @openerpweb.httprequest
    def home(self, req, s_action=None, **kw):
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>'%i for i in self.manifest_list(req, None, 'js'))
        css = "\n        ".join('<link rel="stylesheet" href="%s">'%i for i in self.manifest_list(req, None, 'css'))

        r = html_template % {
            'js': js,
            'css': css,
            'modules': simplejson.dumps(self.server_wide_modules(req)),
            'init': 'var wc = new s.web.WebClient();wc.appendTo($(document.body));'
        }
        return r

    @openerpweb.httprequest
    def login(self, req, db, login, key):
        req.session.authenticate(db, login, key, {})
        redirect = werkzeug.utils.redirect('/web/webclient/home', 303)
        cookie_val = urllib2.quote(simplejson.dumps(req.session_id))
        redirect.set_cookie('instance0|session_id', cookie_val)
        return redirect

    @openerpweb.jsonrequest
    def translations(self, req, mods, lang):
        lang_model = req.session.model('res.lang')
        ids = lang_model.search([("code", "=", lang)])
        if ids:
            lang_obj = lang_model.read(ids[0], ["direction", "date_format", "time_format",
                                                "grouping", "decimal_point", "thousands_sep"])
        else:
            lang_obj = None

        if "_" in lang:
            separator = "_"
        else:
            separator = "@"
        langs = lang.split(separator)
        langs = [separator.join(langs[:x]) for x in range(1, len(langs) + 1)]

        messages = {}
        for mod in mods:
            messages[mod] = {"messages":[]}
            proxy = req.session.proxy("translation")
            messages[mod] = proxy.load(req.session._db, [mod], langs, "web")
        #  keep loading from .po (Reason to run web without embedded mode)
        if not messages['web']['messages']:
            for addon_name in mods:
                transl = {'messages':[]}
                messages[addon_name] = transl
                addons_path = openerpweb.addons_manifest[addon_name]['addons_path']
                for l in langs:
                    f_name = os.path.join(addons_path, addon_name, "i18n", l + ".po")
                    if not os.path.exists(f_name):
                        continue
                    try:
                        with open(f_name) as t_file:
                            po = babel.messages.pofile.read_po(t_file)
                    except Exception:
                        continue
                    for x in po:
                        if x.id and x.string and "openerp-web" in x.auto_comments:
                            transl["messages"].append({'id': x.id, 'string': x.string})
        return {"modules": messages,
                "lang_parameters": lang_obj} 

    @openerpweb.jsonrequest
    def version_info(self, req):
        return {
            "version": common.release.version
        }

class Proxy(openerpweb.Controller):
    _cp_path = '/web/proxy'

    @openerpweb.jsonrequest
    def load(self, req, path):
        """ Proxies an HTTP request through a JSON request.

        It is strongly recommended to not request binary files through this,
        as the result will be a binary data blob as well.

        :param req: OpenERP request
        :param path: actual request path
        :return: file content
        """
        from werkzeug.test import Client
        from werkzeug.wrappers import BaseResponse

        return Client(req.httprequest.app, BaseResponse).get(path).data

class Database(openerpweb.Controller):
    _cp_path = "/web/database"

    @openerpweb.jsonrequest
    def get_list(self, req):
        proxy = req.session.proxy("db")
        dbs = proxy.list()
        h = req.httprequest.environ['HTTP_HOST'].split(':')[0]
        d = h.split('.')[0]
        r = req.config.dbfilter.replace('%h', h).replace('%d', d)
        dbs = [i for i in dbs if re.match(r, i)]
        return {"db_list": dbs}

    @openerpweb.jsonrequest
    def create(self, req, fields):
        params = dict(map(operator.itemgetter('name', 'value'), fields))
        create_attrs = (
            params['super_admin_pwd'],
            params['db_name'],
            bool(params.get('demo_data')),
            params['db_lang'],
            params['create_admin_pwd']
        )

        return req.session.proxy("db").create_database(*create_attrs)

    @openerpweb.jsonrequest
    def drop(self, req, fields):
        password, db = operator.itemgetter(
            'drop_pwd', 'drop_db')(
                dict(map(operator.itemgetter('name', 'value'), fields)))

        try:
            return req.session.proxy("db").drop(password, db)
        except xmlrpclib.Fault, e:
            if e.faultCode and e.faultCode.split(':')[0] == 'AccessDenied':
                return {'error': e.faultCode, 'title': 'Drop Database'}
        return {'error': 'Could not drop database !', 'title': 'Drop Database'}

    @openerpweb.httprequest
    def backup(self, req, backup_db, backup_pwd, token):
        try:
            db_dump = base64.b64decode(
                req.session.proxy("db").dump(backup_pwd, backup_db))
            filename = "%(db)s_%(timestamp)s.dump" % {
                'db': backup_db,
                'timestamp': datetime.datetime.utcnow().strftime(
                    "%Y-%m-%d_%H-%M-%SZ")
            }
            return req.make_response(db_dump,
               [('Content-Type', 'application/octet-stream; charset=binary'),
               ('Content-Disposition', 'attachment; filename="' + filename + '"')],
               {'fileToken': int(token)}
            )
        except xmlrpclib.Fault, e:
             return simplejson.dumps([[],[{'error': e.faultCode, 'title': 'backup Database'}]])

    @openerpweb.httprequest
    def restore(self, req, db_file, restore_pwd, new_db):
        try:
            data = base64.b64encode(db_file.read())
            req.session.proxy("db").restore(restore_pwd, new_db, data)
            return ''
        except xmlrpclib.Fault, e:
            if e.faultCode and e.faultCode.split(':')[0] == 'AccessDenied':
                raise Exception("AccessDenied")

    @openerpweb.jsonrequest
    def change_password(self, req, fields):
        old_password, new_password = operator.itemgetter(
            'old_pwd', 'new_pwd')(
                dict(map(operator.itemgetter('name', 'value'), fields)))
        try:
            return req.session.proxy("db").change_admin_password(old_password, new_password)
        except xmlrpclib.Fault, e:
            if e.faultCode and e.faultCode.split(':')[0] == 'AccessDenied':
                return {'error': e.faultCode, 'title': 'Change Password'}
        return {'error': 'Error, password not changed !', 'title': 'Change Password'}

def topological_sort(modules):
    """ Return a list of module names sorted so that their dependencies of the
    modules are listed before the module itself

    modules is a dict of {module_name: dependencies}

    :param modules: modules to sort
    :type modules: dict
    :returns: list(str)
    """

    dependencies = set(itertools.chain.from_iterable(modules.itervalues()))
    # incoming edge: dependency on other module (if a depends on b, a has an
    # incoming edge from b, aka there's an edge from b to a)
    # outgoing edge: other module depending on this one

    # [Tarjan 1976], http://en.wikipedia.org/wiki/Topological_sorting#Algorithms
    #L ← Empty list that will contain the sorted nodes
    L = []
    #S ← Set of all nodes with no outgoing edges (modules on which no other
    #    module depends)
    S = set(module for module in modules if module not in dependencies)

    visited = set()
    #function visit(node n)
    def visit(n):
        #if n has not been visited yet then
        if n not in visited:
            #mark n as visited
            visited.add(n)
            #change: n not web module, can not be resolved, ignore
            if n not in modules: return
            #for each node m with an edge from m to n do (dependencies of n)
            for m in modules[n]:
                #visit(m)
                visit(m)
            #add n to L
            L.append(n)
    #for each node n in S do
    for n in S:
        #visit(n)
        visit(n)
    return L

class Session(openerpweb.Controller):
    _cp_path = "/web/session"

    def session_info(self, req):
        req.session.ensure_valid()
        return {
            "session_id": req.session_id,
            "uid": req.session._uid,
            "context": req.session.get_context() if req.session._uid else {},
            "db": req.session._db,
            "login": req.session._login,
            "openerp_entreprise": req.session.openerp_entreprise(),
        }

    @openerpweb.jsonrequest
    def get_session_info(self, req):
        return self.session_info(req)

    @openerpweb.jsonrequest
    def authenticate(self, req, db, login, password, base_location=None):
        wsgienv = req.httprequest.environ
        release = common.release
        env = dict(
            base_location=base_location,
            HTTP_HOST=wsgienv['HTTP_HOST'],
            REMOTE_ADDR=wsgienv['REMOTE_ADDR'],
            user_agent="%s / %s" % (release.name, release.version),
        )
        req.session.authenticate(db, login, password, env)

        return self.session_info(req)

    @openerpweb.jsonrequest
    def change_password (self,req,fields):
        old_password, new_password,confirm_password = operator.itemgetter('old_pwd', 'new_password','confirm_pwd')(
                dict(map(operator.itemgetter('name', 'value'), fields)))
        if not (old_password.strip() and new_password.strip() and confirm_password.strip()):
            return {'error':'All passwords have to be filled.','title': 'Change Password'}
        if new_password != confirm_password:
            return {'error': 'The new password and its confirmation must be identical.','title': 'Change Password'}
        try:
            if req.session.model('res.users').change_password(
                old_password, new_password):
                return {'new_password':new_password}
        except Exception:
            return {'error': 'Original password incorrect, your password was not changed.', 'title': 'Change Password'}
        return {'error': 'Error, password not changed !', 'title': 'Change Password'}

    @openerpweb.jsonrequest
    def sc_list(self, req):
        return req.session.model('ir.ui.view_sc').get_sc(
            req.session._uid, "ir.ui.menu", req.session.eval_context(req.context))

    @openerpweb.jsonrequest
    def get_lang_list(self, req):
        try:
            return {
                'lang_list': (req.session.proxy("db").list_lang() or []),
                'error': ""
            }
        except Exception, e:
            return {"error": e, "title": "Languages"}

    @openerpweb.jsonrequest
    def modules(self, req):
        # Compute available candidates module
        loadable = openerpweb.addons_manifest
        loaded = set(req.config.server_wide_modules)
        candidates = [mod for mod in loadable if mod not in loaded]

        # already installed modules have no dependencies
        modules = dict.fromkeys(loaded, [])

        # Compute auto_install modules that might be on the web side only
        modules.update((name, openerpweb.addons_manifest[name].get('depends', []))
                      for name in candidates
                      if openerpweb.addons_manifest[name].get('auto_install'))

        # Retrieve database installed modules
        Modules = req.session.model('ir.module.module')
        for module in Modules.search_read(
                        [('state','=','installed'), ('name','in', candidates)],
                        ['name', 'dependencies_id']):
            deps = module.get('dependencies_id')
            if deps:
                dependencies = map(
                    operator.itemgetter('name'),
                    req.session.model('ir.module.module.dependency').read(deps, ['name']))
                modules[module['name']] = list(
                    set(modules.get(module['name'], []) + dependencies))

        sorted_modules = topological_sort(modules)
        return [module for module in sorted_modules if module not in loaded]

    @openerpweb.jsonrequest
    def eval_domain_and_context(self, req, contexts, domains,
                                group_by_seq=None):
        """ Evaluates sequences of domains and contexts, composing them into
        a single context, domain or group_by sequence.

        :param list contexts: list of contexts to merge together. Contexts are
                              evaluated in sequence, all previous contexts
                              are part of their own evaluation context
                              (starting at the session context).
        :param list domains: list of domains to merge together. Domains are
                             evaluated in sequence and appended to one another
                             (implicit AND), their evaluation domain is the
                             result of merging all contexts.
        :param list group_by_seq: list of domains (which may be in a different
                                  order than the ``contexts`` parameter),
                                  evaluated in sequence, their ``'group_by'``
                                  key is extracted if they have one.
        :returns:
            a 3-dict of:

            context (``dict``)
                the global context created by merging all of
                ``contexts``

            domain (``list``)
                the concatenation of all domains

            group_by (``list``)
                a list of fields to group by, potentially empty (in which case
                no group by should be performed)
        """
        context, domain = eval_context_and_domain(req.session,
                                                  common.nonliterals.CompoundContext(*(contexts or [])),
                                                  common.nonliterals.CompoundDomain(*(domains or [])))

        group_by_sequence = []
        for candidate in (group_by_seq or []):
            ctx = req.session.eval_context(candidate, context)
            group_by = ctx.get('group_by')
            if not group_by:
                continue
            elif isinstance(group_by, basestring):
                group_by_sequence.append(group_by)
            else:
                group_by_sequence.extend(group_by)

        return {
            'context': context,
            'domain': domain,
            'group_by': group_by_sequence
        }

    @openerpweb.jsonrequest
    def save_session_action(self, req, the_action):
        """
        This method store an action object in the session object and returns an integer
        identifying that action. The method get_session_action() can be used to get
        back the action.

        :param the_action: The action to save in the session.
        :type the_action: anything
        :return: A key identifying the saved action.
        :rtype: integer
        """
        saved_actions = req.httpsession.get('saved_actions')
        if not saved_actions:
            saved_actions = {"next":0, "actions":{}}
            req.httpsession['saved_actions'] = saved_actions
        # we don't allow more than 10 stored actions
        if len(saved_actions["actions"]) >= 10:
            del saved_actions["actions"][min(saved_actions["actions"])]
        key = saved_actions["next"]
        saved_actions["actions"][key] = the_action
        saved_actions["next"] = key + 1
        return key

    @openerpweb.jsonrequest
    def get_session_action(self, req, key):
        """
        Gets back a previously saved action. This method can return None if the action
        was saved since too much time (this case should be handled in a smart way).

        :param key: The key given by save_session_action()
        :type key: integer
        :return: The saved action or None.
        :rtype: anything
        """
        saved_actions = req.httpsession.get('saved_actions')
        if not saved_actions:
            return None
        return saved_actions["actions"].get(key)

    @openerpweb.jsonrequest
    def check(self, req):
        req.session.assert_valid()
        return None

    @openerpweb.jsonrequest
    def destroy(self, req):
        req.session._suicide = True

def eval_context_and_domain(session, context, domain=None):
    e_context = session.eval_context(context)
    # should we give the evaluated context as an evaluation context to the domain?
    e_domain = session.eval_domain(domain or [])

    return e_context, e_domain

def load_actions_from_ir_values(req, key, key2, models, meta):
    context = req.session.eval_context(req.context)
    Values = req.session.model('ir.values')
    actions = Values.get(key, key2, models, meta, context)

    return [(id, name, clean_action(req, action))
            for id, name, action in actions]

def clean_action(req, action, do_not_eval=False):
    action.setdefault('flags', {})

    context = req.session.eval_context(req.context)
    eval_ctx = req.session.evaluation_context(context)

    if not do_not_eval:
        # values come from the server, we can just eval them
        if action.get('context') and isinstance(action.get('context'), basestring):
            action['context'] = eval( action['context'], eval_ctx ) or {}

        if action.get('domain') and isinstance(action.get('domain'), basestring):
            action['domain'] = eval( action['domain'], eval_ctx ) or []
    else:
        if 'context' in action:
            action['context'] = parse_context(action['context'], req.session)
        if 'domain' in action:
            action['domain'] = parse_domain(action['domain'], req.session)

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

    id_form = None
    for index, (id, mode) in enumerate(action['views']):
        if mode == 'form':
            id_form = id
            break

    if action.pop('view_type', 'form') != 'form':
        return action

    action['views'] = [
        [id, mode if mode != 'tree' else 'list']
        for id, mode in action['views']
    ]

    return action

class Menu(openerpweb.Controller):
    _cp_path = "/web/menu"

    @openerpweb.jsonrequest
    def load(self, req):
        return {'data': self.do_load(req)}

    @openerpweb.jsonrequest
    def get_user_roots(self, req):
        return self.do_get_user_roots(req)

    def do_get_user_roots(self, req):
        """ Return all root menu ids visible for the session user.

        :param req: A request object, with an OpenERP session attribute
        :type req: < session -> OpenERPSession >
        :return: the root menu ids
        :rtype: list(int)
        """
        s = req.session
        context = s.eval_context(req.context)
        Menus = s.model('ir.ui.menu')
        # If a menu action is defined use its domain to get the root menu items
        user_menu_id = s.model('res.users').read([s._uid], ['menu_id'], context)[0]['menu_id']

        menu_domain = [('parent_id', '=', False)]
        if user_menu_id:
            domain_string = s.model('ir.actions.act_window').read([user_menu_id[0]], ['domain'], context)[0]['domain']
            if domain_string:
                menu_domain = ast.literal_eval(domain_string)

        return Menus.search(menu_domain, 0, False, False, context)

    def do_load(self, req):
        """ Loads all menu items (all applications and their sub-menus).

        :param req: A request object, with an OpenERP session attribute
        :type req: < session -> OpenERPSession >
        :return: the menu root
        :rtype: dict('children': menu_nodes)
        """
        context = req.session.eval_context(req.context)
        Menus = req.session.model('ir.ui.menu')

        menu_roots = Menus.read(self.do_get_user_roots(req), ['name', 'sequence', 'parent_id', 'action', 'needaction_enabled', 'needaction_counter'], context)
        menu_root = {'id': False, 'name': 'root', 'parent_id': [-1, ''], 'children' : menu_roots}

        # menus are loaded fully unlike a regular tree view, cause there are a
        # limited number of items (752 when all 6.1 addons are installed)
        menu_ids = Menus.search([], 0, False, False, context)
        menu_items = Menus.read(menu_ids, ['name', 'sequence', 'parent_id', 'action', 'needaction_enabled', 'needaction_counter'], context)
        # adds roots at the end of the sequence, so that they will overwrite
        # equivalent menu items from full menu read when put into id:item
        # mapping, resulting in children being correctly set on the roots.
        menu_items.extend(menu_roots)

        # make a tree using parent_id
        menu_items_map = dict((menu_item["id"], menu_item) for menu_item in menu_items)
        for menu_item in menu_items:
            if menu_item['parent_id']:
                parent = menu_item['parent_id'][0]
            else:
                parent = False
            if parent in menu_items_map:
                menu_items_map[parent].setdefault(
                    'children', []).append(menu_item)

        # sort by sequence a tree using parent_id
        for menu_item in menu_items:
            menu_item.setdefault('children', []).sort(
                key=operator.itemgetter('sequence'))

        return menu_root

    @openerpweb.jsonrequest
    def action(self, req, menu_id):
        actions = load_actions_from_ir_values(req,'action', 'tree_but_open',
                                             [('ir.ui.menu', menu_id)], False)
        return {"action": actions}

class DataSet(openerpweb.Controller):
    _cp_path = "/web/dataset"

    @openerpweb.jsonrequest
    def search_read(self, req, model, fields=False, offset=0, limit=False, domain=None, sort=None):
        return self.do_search_read(req, model, fields, offset, limit, domain, sort)
    def do_search_read(self, req, model, fields=False, offset=0, limit=False, domain=None
                       , sort=None):
        """ Performs a search() followed by a read() (if needed) using the
        provided search criteria

        :param req: a JSON-RPC request object
        :type req: openerpweb.JsonRequest
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
        Model = req.session.model(model)

        context, domain = eval_context_and_domain(
            req.session, req.context, domain)

        ids = Model.search(domain, offset or 0, limit or False, sort or False, context)
        if limit and len(ids) == limit:
            length = Model.search_count(domain, context)
        else:
            length = len(ids) + (offset or 0)
        if fields and fields == ['id']:
            # shortcut read if we only want the ids
            return {
                'length': length,
                'records': [{'id': id} for id in ids]
            }

        records = Model.read(ids, fields or False, context)
        records.sort(key=lambda obj: ids.index(obj['id']))
        return {
            'length': length,
            'records': records
        }

    @openerpweb.jsonrequest
    def load(self, req, model, id, fields):
        m = req.session.model(model)
        value = {}
        r = m.read([id], False, req.session.eval_context(req.context))
        if r:
            value = r[0]
        return {'value': value}

    def call_common(self, req, model, method, args, domain_id=None, context_id=None):
        has_domain = domain_id is not None and domain_id < len(args)
        has_context = context_id is not None and context_id < len(args)

        domain = args[domain_id] if has_domain else []
        context = args[context_id] if has_context else {}
        c, d = eval_context_and_domain(req.session, context, domain)
        if has_domain:
            args[domain_id] = d
        if has_context:
            args[context_id] = c

        return self._call_kw(req, model, method, args, {})
    
    def _call_kw(self, req, model, method, args, kwargs):
        for i in xrange(len(args)):
            if isinstance(args[i], common.nonliterals.BaseContext):
                args[i] = req.session.eval_context(args[i])
            elif isinstance(args[i], common.nonliterals.BaseDomain):
                args[i] = req.session.eval_domain(args[i])
        for k in kwargs.keys():
            if isinstance(kwargs[k], common.nonliterals.BaseContext):
                kwargs[k] = req.session.eval_context(kwargs[k])
            elif isinstance(kwargs[k], common.nonliterals.BaseDomain):
                kwargs[k] = req.session.eval_domain(kwargs[k])

        return getattr(req.session.model(model), method)(*args, **kwargs)

    @openerpweb.jsonrequest
    def onchange(self, req, model, method, args, context_id=None):
        """ Support method for handling onchange calls: behaves much like call
        with the following differences:

        * Does not take a domain_id
        * Is aware of the return value's structure, and will parse the domains
          if needed in order to return either parsed literal domains (in JSON)
          or non-literal domain instances, allowing those domains to be used
          from JS

        :param req:
        :type req: web.common.http.JsonRequest
        :param str model: object type on which to call the method
        :param str method: name of the onchange handler method
        :param list args: arguments to call the onchange handler with
        :param int context_id: index of the context object in the list of
                               arguments
        :return: result of the onchange call with all domains parsed
        """
        result = self.call_common(req, model, method, args, context_id=context_id)
        if not result or 'domain' not in result:
            return result

        result['domain'] = dict(
            (k, parse_domain(v, req.session))
            for k, v in result['domain'].iteritems())

        return result

    @openerpweb.jsonrequest
    def call(self, req, model, method, args, domain_id=None, context_id=None):
        return self.call_common(req, model, method, args, domain_id, context_id)
    
    @openerpweb.jsonrequest
    def call_kw(self, req, model, method, args, kwargs):
        return self._call_kw(req, model, method, args, kwargs)

    @openerpweb.jsonrequest
    def call_button(self, req, model, method, args, domain_id=None, context_id=None):
        action = self.call_common(req, model, method, args, domain_id, context_id)
        if isinstance(action, dict) and action.get('type') != '':
            return {'result': clean_action(req, action)}
        return {'result': False}

    @openerpweb.jsonrequest
    def exec_workflow(self, req, model, id, signal):
        return req.session.exec_workflow(model, id, signal)

class DataGroup(openerpweb.Controller):
    _cp_path = "/web/group"
    @openerpweb.jsonrequest
    def read(self, req, model, fields, group_by_fields, domain=None, sort=None):
        Model = req.session.model(model)
        context, domain = eval_context_and_domain(req.session, req.context, domain)

        return Model.read_group(
            domain or [], fields, group_by_fields, 0, False,
            dict(context, group_by=group_by_fields), sort or False)

class View(openerpweb.Controller):
    _cp_path = "/web/view"

    def fields_view_get(self, req, model, view_id, view_type,
                        transform=True, toolbar=False, submenu=False):
        Model = req.session.model(model)
        context = req.session.eval_context(req.context)
        fvg = Model.fields_view_get(view_id, view_type, context, toolbar, submenu)
        # todo fme?: check that we should pass the evaluated context here
        self.process_view(req.session, fvg, context, transform, (view_type == 'kanban'))
        if toolbar and transform:
            self.process_toolbar(req, fvg['toolbar'])
        return fvg

    def process_view(self, session, fvg, context, transform, preserve_whitespaces=False):
        # depending on how it feels, xmlrpclib.ServerProxy can translate
        # XML-RPC strings to ``str`` or ``unicode``. ElementTree does not
        # enjoy unicode strings which can not be trivially converted to
        # strings, and it blows up during parsing.

        # So ensure we fix this retardation by converting view xml back to
        # bit strings.
        if isinstance(fvg['arch'], unicode):
            arch = fvg['arch'].encode('utf-8')
        else:
            arch = fvg['arch']
        fvg['arch_string'] = arch

        if transform:
            evaluation_context = session.evaluation_context(context or {})
            xml = self.transform_view(arch, session, evaluation_context)
        else:
            xml = ElementTree.fromstring(arch)
        fvg['arch'] = common.xml2json.from_elementtree(xml, preserve_whitespaces)

        if 'id' in fvg['fields']:
            # Special case for id's
            id_field = fvg['fields']['id']
            id_field['original_type'] = id_field['type']
            id_field['type'] = 'id'

        for field in fvg['fields'].itervalues():
            if field.get('views'):
                for view in field["views"].itervalues():
                    self.process_view(session, view, None, transform)
            if field.get('domain'):
                field["domain"] = parse_domain(field["domain"], session)
            if field.get('context'):
                field["context"] = parse_context(field["context"], session)

    def process_toolbar(self, req, toolbar):
        """
        The toolbar is a mapping of section_key: [action_descriptor]

        We need to clean all those actions in order to ensure correct
        round-tripping
        """
        for actions in toolbar.itervalues():
            for action in actions:
                if 'context' in action:
                    action['context'] = parse_context(
                        action['context'], req.session)
                if 'domain' in action:
                    action['domain'] = parse_domain(
                        action['domain'], req.session)

    @openerpweb.jsonrequest
    def add_custom(self, req, view_id, arch):
        CustomView = req.session.model('ir.ui.view.custom')
        CustomView.create({
            'user_id': req.session._uid,
            'ref_id': view_id,
            'arch': arch
        }, req.session.eval_context(req.context))
        return {'result': True}

    @openerpweb.jsonrequest
    def undo_custom(self, req, view_id, reset=False):
        CustomView = req.session.model('ir.ui.view.custom')
        context = req.session.eval_context(req.context)
        vcustom = CustomView.search([('user_id', '=', req.session._uid), ('ref_id' ,'=', view_id)],
                                    0, False, False, context)
        if vcustom:
            if reset:
                CustomView.unlink(vcustom, context)
            else:
                CustomView.unlink([vcustom[0]], context)
            return {'result': True}
        return {'result': False}

    def transform_view(self, view_string, session, context=None):
        # transform nodes on the fly via iterparse, instead of
        # doing it statically on the parsing result
        parser = ElementTree.iterparse(StringIO(view_string), events=("start",))
        root = None
        for event, elem in parser:
            if event == "start":
                if root is None:
                    root = elem
                self.parse_domains_and_contexts(elem, session)
        return root

    def parse_domains_and_contexts(self, elem, session):
        """ Converts domains and contexts from the view into Python objects,
        either literals if they can be parsed by literal_eval or a special
        placeholder object if the domain or context refers to free variables.

        :param elem: the current node being parsed
        :type param: xml.etree.ElementTree.Element
        :param session: OpenERP session object, used to store and retrieve
                        non-literal objects
        :type session: openerpweb.openerpweb.OpenERPSession
        """
        for el in ['domain', 'filter_domain']:
            domain = elem.get(el, '').strip()
            if domain:
                elem.set(el, parse_domain(domain, session))
                elem.set(el + '_string', domain)
        for el in ['context', 'default_get']:
            context_string = elem.get(el, '').strip()
            if context_string:
                elem.set(el, parse_context(context_string, session))
                elem.set(el + '_string', context_string)

    @openerpweb.jsonrequest
    def load(self, req, model, view_id, view_type, toolbar=False):
        return self.fields_view_get(req, model, view_id, view_type, toolbar=toolbar)

def parse_domain(domain, session):
    """ Parses an arbitrary string containing a domain, transforms it
    to either a literal domain or a :class:`common.nonliterals.Domain`

    :param domain: the domain to parse, if the domain is not a string it
                   is assumed to be a literal domain and is returned as-is
    :param session: Current OpenERP session
    :type session: openerpweb.openerpweb.OpenERPSession
    """
    if not isinstance(domain, basestring):
        return domain
    try:
        return ast.literal_eval(domain)
    except ValueError:
        # not a literal
        return common.nonliterals.Domain(session, domain)

def parse_context(context, session):
    """ Parses an arbitrary string containing a context, transforms it
    to either a literal context or a :class:`common.nonliterals.Context`

    :param context: the context to parse, if the context is not a string it
           is assumed to be a literal domain and is returned as-is
    :param session: Current OpenERP session
    :type session: openerpweb.openerpweb.OpenERPSession
    """
    if not isinstance(context, basestring):
        return context
    try:
        return ast.literal_eval(context)
    except ValueError:
        return common.nonliterals.Context(session, context)

class ListView(View):
    _cp_path = "/web/listview"

    def process_colors(self, view, row, context):
        colors = view['arch']['attrs'].get('colors')

        if not colors:
            return None

        color = [
            pair.split(':')[0]
            for pair in colors.split(';')
            if eval(pair.split(':')[1], dict(context, **row))
        ]

        if not color:
            return None
        elif len(color) == 1:
            return color[0]
        return 'maroon'

class TreeView(View):
    _cp_path = "/web/treeview"

    @openerpweb.jsonrequest
    def action(self, req, model, id):
        return load_actions_from_ir_values(
            req,'action', 'tree_but_open',[(model, id)],
            False)

class SearchView(View):
    _cp_path = "/web/searchview"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        fields_view = self.fields_view_get(req, model, view_id, 'search')
        return {'fields_view': fields_view}

    @openerpweb.jsonrequest
    def fields_get(self, req, model):
        Model = req.session.model(model)
        fields = Model.fields_get(False, req.session.eval_context(req.context))
        for field in fields.values():
            # shouldn't convert the views too?
            if field.get('domain'):
                field["domain"] = parse_domain(field["domain"], req.session)
            if field.get('context'):
                field["context"] = parse_context(field["context"], req.session)
        return {'fields': fields}

    @openerpweb.jsonrequest
    def get_filters(self, req, model):
        logger = logging.getLogger(__name__ + '.SearchView.get_filters')
        Model = req.session.model("ir.filters")
        filters = Model.get_filters(model)
        for filter in filters:
            try:
                parsed_context = parse_context(filter["context"], req.session)
                filter["context"] = (parsed_context
                        if not isinstance(parsed_context, common.nonliterals.BaseContext)
                        else req.session.eval_context(parsed_context))

                parsed_domain = parse_domain(filter["domain"], req.session)
                filter["domain"] = (parsed_domain
                        if not isinstance(parsed_domain, common.nonliterals.BaseDomain)
                        else req.session.eval_domain(parsed_domain))
            except Exception:
                logger.exception("Failed to parse custom filter %s in %s",
                                 filter['name'], model)
                filter['disabled'] = True
                del filter['context']
                del filter['domain']
        return filters
    
     
    @openerpweb.jsonrequest
    def add_to_dashboard(self, req, menu_id, action_id, context_to_save, domain, view_mode, name=''):
        to_eval = common.nonliterals.CompoundContext(context_to_save)
        to_eval.session = req.session
        ctx = dict((k, v) for k, v in to_eval.evaluate().iteritems()
                   if not k.startswith('search_default_'))
        ctx['dashboard_merge_domains_contexts'] = False # TODO: replace this 6.1 workaround by attribute on <action/>
        domain = common.nonliterals.CompoundDomain(domain)
        domain.session = req.session
        domain = domain.evaluate()

        dashboard_action = load_actions_from_ir_values(req, 'action', 'tree_but_open',
                                             [('ir.ui.menu', menu_id)], False)
        if dashboard_action:
            action = dashboard_action[0][2]
            if action['res_model'] == 'board.board' and action['views'][0][1] == 'form':
                # Maybe should check the content instead of model board.board ?
                view_id = action['views'][0][0]
                board = req.session.model(action['res_model']).fields_view_get(view_id, 'form')
                if board and 'arch' in board:
                    xml = ElementTree.fromstring(board['arch'])
                    column = xml.find('./board/column')
                    if column is not None:
                        new_action = ElementTree.Element('action', {
                                'name' : str(action_id),
                                'string' : name,
                                'view_mode' : view_mode,
                                'context' : str(ctx),
                                'domain' : str(domain)
                            })
                        column.insert(0, new_action)
                        arch = ElementTree.tostring(xml, 'utf-8')
                        return req.session.model('ir.ui.view.custom').create({
                                'user_id': req.session._uid,
                                'ref_id': view_id,
                                'arch': arch
                            }, req.session.eval_context(req.context))

        return False

class Binary(openerpweb.Controller):
    _cp_path = "/web/binary"

    @openerpweb.httprequest
    def image(self, req, model, id, field, **kw):
        last_update = '__last_update'
        Model = req.session.model(model)
        context = req.session.eval_context(req.context)
        headers = [('Content-Type', 'image/png')]
        etag = req.httprequest.headers.get('If-None-Match')
        hashed_session = hashlib.md5(req.session_id).hexdigest()
        if etag:
            if not id and hashed_session == etag:
                return werkzeug.wrappers.Response(status=304)
            else:
                date = Model.read([int(id)], [last_update], context)[0].get(last_update)
                if hashlib.md5(date).hexdigest() == etag:
                    return werkzeug.wrappers.Response(status=304)

        retag = hashed_session
        try:
            if not id:
                res = Model.default_get([field], context).get(field)
                image_data = base64.b64decode(res)
            else:
                res = Model.read([int(id)], [last_update, field], context)[0]
                retag = hashlib.md5(res.get(last_update)).hexdigest()
                image_data = base64.b64decode(res.get(field))
        except (TypeError, xmlrpclib.Fault):
            image_data = self.placeholder(req)
        headers.append(('ETag', retag))
        headers.append(('Content-Length', len(image_data)))
        try:
            ncache = int(kw.get('cache'))
            headers.append(('Cache-Control', 'no-cache' if ncache == 0 else 'max-age=%s' % (ncache)))
        except:
            pass
        return req.make_response(image_data, headers)
    def placeholder(self, req):
        addons_path = openerpweb.addons_manifest['web']['addons_path']
        return open(os.path.join(addons_path, 'web', 'static', 'src', 'img', 'placeholder.png'), 'rb').read()
    def content_disposition(self, filename, req):
        filename = filename.encode('utf8')
        escaped = urllib2.quote(filename)
        browser = req.httprequest.user_agent.browser
        version = int((req.httprequest.user_agent.version or '0').split('.')[0])
        if browser == 'msie' and version < 9:
            return "attachment; filename=%s" % escaped
        elif browser == 'safari':
            return "attachment; filename=%s" % filename
        else:
            return "attachment; filename*=UTF-8''%s" % escaped

    @openerpweb.httprequest
    def saveas(self, req, model, field, id=None, filename_field=None, **kw):
        """ Download link for files stored as binary fields.

        If the ``id`` parameter is omitted, fetches the default value for the
        binary field (via ``default_get``), otherwise fetches the field for
        that precise record.

        :param req: OpenERP request
        :type req: :class:`web.common.http.HttpRequest`
        :param str model: name of the model to fetch the binary from
        :param str field: binary field
        :param str id: id of the record from which to fetch the binary
        :param str filename_field: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        Model = req.session.model(model)
        context = req.session.eval_context(req.context)
        fields = [field]
        if filename_field:
            fields.append(filename_field)
        if id:
            res = Model.read([int(id)], fields, context)[0]
        else:
            res = Model.default_get(fields, context)
        filecontent = base64.b64decode(res.get(field, ''))
        if not filecontent:
            return req.not_found()
        else:
            filename = '%s_%s' % (model.replace('.', '_'), id)
            if filename_field:
                filename = res.get(filename_field, '') or filename
            return req.make_response(filecontent,
                [('Content-Type', 'application/octet-stream'),
                 ('Content-Disposition', self.content_disposition(filename, req))])

    @openerpweb.httprequest
    def saveas_ajax(self, req, data, token):
        jdata = simplejson.loads(data)
        model = jdata['model']
        field = jdata['field']
        id = jdata.get('id', None)
        filename_field = jdata.get('filename_field', None)
        context = jdata.get('context', dict())

        context = req.session.eval_context(context)
        Model = req.session.model(model)
        fields = [field]
        if filename_field:
            fields.append(filename_field)
        if id:
            res = Model.read([int(id)], fields, context)[0]
        else:
            res = Model.default_get(fields, context)
        filecontent = base64.b64decode(res.get(field, ''))
        if not filecontent:
            raise ValueError("No content found for field '%s' on '%s:%s'" %
                (field, model, id))
        else:
            filename = '%s_%s' % (model.replace('.', '_'), id)
            if filename_field:
                filename = res.get(filename_field, '') or filename
            return req.make_response(filecontent,
                headers=[('Content-Type', 'application/octet-stream'),
                        ('Content-Disposition', self.content_disposition(filename, req))],
                cookies={'fileToken': int(token)})

    @openerpweb.httprequest
    def upload(self, req, callback, ufile):
        # TODO: might be useful to have a configuration flag for max-length file uploads
        try:
            out = """<script language="javascript" type="text/javascript">
                        var win = window.top.window;
                        win.jQuery(win).trigger(%s, %s);
                    </script>"""
            data = ufile.read()
            args = [len(data), ufile.filename,
                    ufile.content_type, base64.b64encode(data)]
        except Exception, e:
            args = [False, e.message]
        return out % (simplejson.dumps(callback), simplejson.dumps(args))

    @openerpweb.httprequest
    def upload_attachment(self, req, callback, model, id, ufile):
        context = req.session.eval_context(req.context)
        Model = req.session.model('ir.attachment')
        try:
            out = """<script language="javascript" type="text/javascript">
                        var win = window.top.window;
                        win.jQuery(win).trigger(%s, %s);
                    </script>"""
            attachment_id = Model.create({
                'name': ufile.filename,
                'datas': base64.encodestring(ufile.read()),
                'datas_fname': ufile.filename,
                'res_model': model,
                'res_id': int(id)
            }, context)
            args = {
                'filename': ufile.filename,
                'id':  attachment_id
            }
        except Exception, e:
            args = { 'error': e.message }
        return out % (simplejson.dumps(callback), simplejson.dumps(args))

class Action(openerpweb.Controller):
    _cp_path = "/web/action"
    
    action_mapping = {
        "ir.actions.act_url": "ir.actions.url",
    }

    # For most actions, the type attribute and the model name are the same, but
    # there are exceptions. This dict is used to remap action type attributes
    # to the "real" model name when they differ.
    action_mapping = {
        "ir.actions.act_url": "ir.actions.url",
    }

    @openerpweb.jsonrequest
    def load(self, req, action_id, do_not_eval=False):
        Actions = req.session.model('ir.actions.actions')
        value = False
        context = req.session.eval_context(req.context)
        base_action = Actions.read([action_id], ['type'], context)
        if base_action:
            ctx = {}
            action_type = base_action[0]['type']
            if action_type == 'ir.actions.report.xml':
                ctx.update({'bin_size': True})
            ctx.update(context)
            action_model = self.action_mapping.get(action_type, action_type)
            action = req.session.model(action_model).read([action_id], False, ctx)
            if action:
                value = clean_action(req, action[0], do_not_eval)
        return {'result': value}

    @openerpweb.jsonrequest
    def run(self, req, action_id):
        return_action = req.session.model('ir.actions.server').run(
            [action_id], req.session.eval_context(req.context))
        if return_action:
            return clean_action(req, return_action)
        else:
            return False

class Export(View):
    _cp_path = "/web/export"

    @openerpweb.jsonrequest
    def formats(self, req):
        """ Returns all valid export formats

        :returns: for each export format, a pair of identifier and printable name
        :rtype: [(str, str)]
        """
        return sorted([
            controller.fmt
            for path, controller in openerpweb.controllers_path.iteritems()
            if path.startswith(self._cp_path)
            if hasattr(controller, 'fmt')
        ], key=operator.itemgetter("label"))

    def fields_get(self, req, model):
        Model = req.session.model(model)
        fields = Model.fields_get(False, req.session.eval_context(req.context))
        return fields

    @openerpweb.jsonrequest
    def get_fields(self, req, model, prefix='', parent_name= '',
                   import_compat=True, parent_field_type=None,
                   exclude=None):

        if import_compat and parent_field_type == "many2one":
            fields = {}
        else:
            fields = self.fields_get(req, model)

        if import_compat:
            fields.pop('id', None)
        else:
            fields['.id'] = fields.pop('id', {'string': 'ID'})

        fields_sequence = sorted(fields.iteritems(),
            key=lambda field: field[1].get('string', ''))

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

    @openerpweb.jsonrequest
    def namelist(self,req,  model, export_id):
        # TODO: namelist really has no reason to be in Python (although itertools.groupby helps)
        export = req.session.model("ir.exports").read([export_id])[0]
        export_fields_list = req.session.model("ir.exports.line").read(
            export['export_fields'])

        fields_data = self.fields_info(
            req, model, map(operator.itemgetter('name'), export_fields_list))

        return [
            {'name': field['name'], 'label': fields_data[field['name']]}
            for field in export_fields_list
        ]

    def fields_info(self, req, model, export_fields):
        info = {}
        fields = self.fields_get(req, model)

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
                    req, fields[base]['relation'], base, fields[base]['string'],
                    subfields
                ))
            else:
                info[base] = fields[base]['string']

        return info

    def graft_subfields(self, req, model, prefix, prefix_string, fields):
        export_fields = [field.split('/', 1)[1] for field in fields]
        return (
            (prefix + '/' + k, prefix_string + '/' + v)
            for k, v in self.fields_info(req, model, export_fields).iteritems())

    #noinspection PyPropertyDefinition
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

    @openerpweb.httprequest
    def index(self, req, data, token):
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain',
                                'import_compat')(
                simplejson.loads(data))

        context = req.session.eval_context(req.context)
        Model = req.session.model(model)
        ids = ids or Model.search(domain, 0, False, False, context)

        field_names = map(operator.itemgetter('name'), fields)
        import_data = Model.export_data(ids, field_names, context).get('datas',[])

        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]


        return req.make_response(self.from_data(columns_headers, import_data),
            headers=[('Content-Disposition', 'attachment; filename="%s"' % self.filename(model)),
                     ('Content-Type', self.content_type)],
            cookies={'fileToken': int(token)})

class CSVExport(Export):
    _cp_path = '/web/export/csv'
    fmt = {'tag': 'csv', 'label': 'CSV'}

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
                if isinstance(d, basestring):
                    d = d.replace('\n',' ').replace('\t',' ')
                    try:
                        d = d.encode('utf-8')
                    except UnicodeError:
                        pass
                if d is False: d = None
                row.append(d)
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

class ExcelExport(Export):
    _cp_path = '/web/export/xls'
    fmt = {
        'tag': 'xls',
        'label': 'Excel',
        'error': None if xlwt else "XLWT required"
    }

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

        style = xlwt.easyxf('align: wrap yes')

        for row_index, row in enumerate(rows):
            for cell_index, cell_value in enumerate(row):
                if isinstance(cell_value, basestring):
                    cell_value = re.sub("\r", " ", cell_value)
                if cell_value is False: cell_value = None
                worksheet.write(row_index + 1, cell_index, cell_value, style)

        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

class Reports(View):
    _cp_path = "/web/report"
    POLLING_DELAY = 0.25
    TYPES_MAPPING = {
        'doc': 'application/vnd.ms-word',
        'html': 'text/html',
        'odt': 'application/vnd.oasis.opendocument.text',
        'pdf': 'application/pdf',
        'sxw': 'application/vnd.sun.xml.writer',
        'xls': 'application/vnd.ms-excel',
    }

    @openerpweb.httprequest
    def index(self, req, action, token):
        action = simplejson.loads(action)

        report_srv = req.session.proxy("report")
        context = req.session.eval_context(
            common.nonliterals.CompoundContext(
                req.context or {}, action[ "context"]))

        report_data = {}
        report_ids = context["active_ids"]
        if 'report_type' in action:
            report_data['report_type'] = action['report_type']
        if 'datas' in action:
            if 'ids' in action['datas']:
                report_ids = action['datas'].pop('ids')
            report_data.update(action['datas'])

        report_id = report_srv.report(
            req.session._db, req.session._uid, req.session._password,
            action["report_name"], report_ids,
            report_data, context)

        report_struct = None
        while True:
            report_struct = report_srv.report_get(
                req.session._db, req.session._uid, req.session._password, report_id)
            if report_struct["state"]:
                break

            time.sleep(self.POLLING_DELAY)

        report = base64.b64decode(report_struct['result'])
        if report_struct.get('code') == 'zlib':
            report = zlib.decompress(report)
        report_mimetype = self.TYPES_MAPPING.get(
            report_struct['format'], 'octet-stream')
        file_name = None
        if 'name' not in action:
            reports = req.session.model('ir.actions.report.xml')
            res_id = reports.search([('report_name', '=', action['report_name']),],
                                    0, False, False, context)
            if len(res_id) > 0:
                file_name = reports.read(res_id[0], ['name'], context)['name']
            else:
                file_name = action['report_name']

        return req.make_response(report,
             headers=[
                 # maybe we should take of what characters can appear in a file name?
                 ('Content-Disposition', 'attachment; filename="%s.%s"' % (file_name, report_struct['format'])),
                 ('Content-Type', report_mimetype),
                 ('Content-Length', len(report))],
             cookies={'fileToken': int(token)})

class Import(View):
    _cp_path = "/web/import"

    def fields_get(self, req, model):
        Model = req.session.model(model)
        fields = Model.fields_get(False, req.session.eval_context(req.context))
        return fields

    @openerpweb.httprequest
    def detect_data(self, req, csvfile, csvsep=',', csvdel='"', csvcode='utf-8', jsonp='callback'):
        try:
            data = list(csv.reader(
                csvfile, quotechar=str(csvdel), delimiter=str(csvsep)))
        except csv.Error, e:
            csvfile.seek(0)
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error': {
                    'message': 'Error parsing CSV file: %s' % e,
                    # decodes each byte to a unicode character, which may or
                    # may not be printable, but decoding will succeed.
                    # Otherwise simplejson will try to decode the `str` using
                    # utf-8, which is very likely to blow up on characters out
                    # of the ascii range (in range [128, 256))
                    'preview': csvfile.read(200).decode('iso-8859-1')}}))

        try:
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps(
                    {'records': data[:10]}, encoding=csvcode))
        except UnicodeDecodeError:
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({
                    'message': u"Failed to decode CSV file using encoding %s, "
                               u"try switching to a different encoding" % csvcode
                }))

    @openerpweb.httprequest
    def import_data(self, req, model, csvfile, csvsep, csvdel, csvcode, jsonp,
                    meta):
        modle_obj = req.session.model(model)
        skip, indices, fields = operator.itemgetter('skip', 'indices', 'fields')(
            simplejson.loads(meta))

        error = None
        if not (csvdel and len(csvdel) == 1):
            error = u"The CSV delimiter must be a single character"

        if not indices and fields:
            error = u"You must select at least one field to import"

        if error:
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error': {'message': error}}))

        # skip ignored records (@skip parameter)
        # then skip empty lines (not valid csv)
        # nb: should these operations be reverted?
        rows_to_import = itertools.ifilter(
            None,
            itertools.islice(
                csv.reader(csvfile, quotechar=str(csvdel), delimiter=str(csvsep)),
                skip, None))

        # if only one index, itemgetter will return an atom rather than a tuple
        if len(indices) == 1: mapper = lambda row: [row[indices[0]]]
        else: mapper = operator.itemgetter(*indices)

        data = None
        error = None
        try:
            # decode each data row
            data = [
                [record.decode(csvcode) for record in row]
                for row in itertools.imap(mapper, rows_to_import)
                # don't insert completely empty rows (can happen due to fields
                # filtering in case of e.g. o2m content rows)
                if any(row)
            ]
        except UnicodeDecodeError:
            error = u"Failed to decode CSV file using encoding %s" % csvcode
        except csv.Error, e:
            error = u"Could not process CSV file: %s" % e

        # If the file contains nothing,
        if not data:
            error = u"File to import is empty"
        if error:
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error': {'message': error}}))

        try:
            (code, record, message, _nope) = modle_obj.import_data(
                fields, data, 'init', '', False,
                req.session.eval_context(req.context))
        except xmlrpclib.Fault, e:
            error = {"message": u"%s, %s" % (e.faultCode, e.faultString)}
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error':error}))

        if code != -1:
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'success':True}))

        msg = u"Error during import: %s\n\nTrying to import record %r" % (
            message, record)
        return '<script>window.top.%s(%s);</script>' % (
            jsonp, simplejson.dumps({'error': {'message':msg}}))
