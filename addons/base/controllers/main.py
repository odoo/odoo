# -*- coding: utf-8 -*-

import base64
import csv
import glob
import operator
import os
import re
import simplejson
import textwrap
import xmlrpclib
import time
from xml.etree import ElementTree
from cStringIO import StringIO

import cherrypy

import base.common as openerpweb
import base.common.ast
import base.common.nonliterals
openerpweb.ast = base.common.ast
openerpweb.nonliterals = base.common.nonliterals

from babel.messages.pofile import read_po

_REPORT_POLLER_DELAY = 0.05

# Should move to openerpweb.Xml2Json
class Xml2Json:
    # xml2json-direct
    # Simple and straightforward XML-to-JSON converter in Python
    # New BSD Licensed
    #
    # URL: http://code.google.com/p/xml2json-direct/
    @staticmethod
    def convert_to_json(s):
        return simplejson.dumps(
            Xml2Json.convert_to_structure(s), sort_keys=True, indent=4)

    @staticmethod
    def convert_to_structure(s):
        root = ElementTree.fromstring(s)
        return Xml2Json.convert_element(root)

    @staticmethod
    def convert_element(el, skip_whitespaces=True):
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
        if el.text and (not skip_whitespaces or el.text.strip() != ''):
            kids.append(el.text)
        for kid in el:
            kids.append(Xml2Json.convert_element(kid))
            if kid.tail and (not skip_whitespaces or kid.tail.strip() != ''):
                kids.append(kid.tail)
        res["children"] = kids
        return res

#----------------------------------------------------------
# OpenERP Web base Controllers
#----------------------------------------------------------

def manifest_glob(addons, key):
    files = []
    for addon in addons:
        globlist = openerpweb.addons_manifest.get(addon, {}).get(key, [])
        for pattern in globlist:
            for path in glob.glob(os.path.join(openerpweb.path_addons, addon, pattern)):
                files.append(path[len(openerpweb.path_addons):])
    return files

def concat_files(file_list):
    """ Concatenate file content
    return (concat,timestamp)
    concat: concatenation of file content
    timestamp: max(os.path.getmtime of file_list)
    """
    files_content = []
    files_timestamp = 0
    for i in file_list:
        fname = os.path.join(openerpweb.path_addons, i[1:])
        ftime = os.path.getmtime(fname)
        if ftime > files_timestamp:
            files_timestamp = ftime
        files_content.append(open(fname).read())
    files_concat = "".join(files_content)
    return (files_concat,files_timestamp)

home_template = textwrap.dedent("""<!DOCTYPE html>
<html style="height: 100%%">
    <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8" />
        <title>OpenERP</title>
        <link rel="shortcut icon" href="/base/static/src/img/favicon.ico" type="image/x-icon"/>
        %(css)s
        <!--[if lte IE 7]>
        <link rel="stylesheet" href="/base/static/src/css/base-ie7.css" type="text/css"/>
        <![endif]-->
        %(javascript)s
        <script type="text/javascript">
            $(function() {
                QWeb = new QWeb2.Engine();
                var c = new openerp.init();
                var wc = new c.base.WebClient("oe");
                wc.start();
            });
        </script>
    </head>
    <body id="oe" class="openerp"></body>
</html>
""")
class WebClient(openerpweb.Controller):
    _cp_path = "/base/webclient"

    @openerpweb.jsonrequest
    def csslist(self, req, mods='base'):
        return manifest_glob(mods.split(','), 'css')

    @openerpweb.jsonrequest
    def jslist(self, req, mods='base'):
        return manifest_glob(mods.split(','), 'js')

    @openerpweb.httprequest
    def css(self, req, mods='base'):
        req.httpresponse.headers['Content-Type'] = 'text/css'
        files = manifest_glob(mods.split(','), 'css')
        content,timestamp = concat_files(files)
        # TODO request set the Date of last modif and Etag
        return content

    @openerpweb.httprequest
    def js(self, req, mods='base'):
        req.httpresponse.headers['Content-Type'] = 'application/javascript'
        files = manifest_glob(mods.split(','), 'js')
        content,timestamp = concat_files(files)
        # TODO request set the Date of last modif and Etag
        return content

    @openerpweb.httprequest
    def home(self, req, s_action=None, **kw):
        # script tags
        jslist = ['/base/webclient/js']
        if req.debug:
            jslist = manifest_glob(['base'], 'js')
        js = "\n        ".join(['<script type="text/javascript" src="%s"></script>'%i for i in jslist])

        # css tags
        csslist = ['/base/webclient/css']
        if req.debug:
            csslist = manifest_glob(['base'], 'css')
        css = "\n        ".join(['<link rel="stylesheet" href="%s">'%i for i in csslist])
        r = home_template % {
            'javascript': js,
            'css': css
        }
        return r

    @openerpweb.jsonrequest
    def translations(self, req, mods, lang):
        lang_model = req.session.model('res.lang')
        ids = lang_model.search([("code", "=", lang)])
        if ids:
            lang_obj = lang_model.read(ids[0], ["direction", "date_format", "time_format",
                                                "grouping", "decimal_point", "thousands_sep"])
        else:
            lang_obj = None

        if lang.count("_") > 0:
            separator = "_"
        else:
            separator = "@"
        langs = lang.split(separator)
        langs = [separator.join(langs[:x]) for x in range(1, len(langs) + 1)]

        transs = {}
        for addon_name in mods:
            transl = {"messages":[]}
            transs[addon_name] = transl
            for l in langs:
                f_name = os.path.join(openerpweb.path_addons, addon_name, "po", l + ".po")
                if not os.path.exists(f_name):
                    continue
                try:
                    with open(f_name) as t_file:
                        po = read_po(t_file)
                except:
                    continue
                for x in po:
                    if x.id and x.string:
                        transl["messages"].append({'id': x.id, 'string': x.string})
        return {"modules": transs,
                "lang_parameters": lang_obj}

class Database(openerpweb.Controller):
    _cp_path = "/base/database"

    @openerpweb.jsonrequest
    def get_list(self, req):
        proxy = req.session.proxy("db")
        dbs = proxy.list()
        h = req.httprequest.headers['Host'].split(':')[0]
        d = h.split('.')[0]
        r = cherrypy.config['openerp.dbfilter'].replace('%h', h).replace('%d', d)
        dbs = [i for i in dbs if re.match(r, i)]
        return {"db_list": dbs}

    @openerpweb.jsonrequest
    def progress(self, req, password, id):
        return req.session.proxy('db').get_progress(password, id)

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

        try:
            return req.session.proxy("db").create(*create_attrs)
        except xmlrpclib.Fault, e:
            if e.faultCode and e.faultCode.split(':')[0] == 'AccessDenied':
                return {'error': e.faultCode, 'title': 'Create Database'}
        return {'error': 'Could not create database !', 'title': 'Create Database'}

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
            db_dump = base64.decodestring(
                req.session.proxy("db").dump(backup_pwd, backup_db))
            req.httpresponse.headers['Content-Type'] = "application/octet-stream; charset=binary"
            req.httpresponse.headers['Content-Disposition'] = 'attachment; filename="' + backup_db + '.dump"'
            req.httpresponse.cookie['fileToken'] = token
            req.httpresponse.cookie['fileToken']['path'] = '/'
            return db_dump
        except xmlrpclib.Fault, e:
            if e.faultCode and e.faultCode.split(':')[0] == 'AccessDenied':
                return 'Backup Database|' + e.faultCode
        return 'Backup Database|Could not generate database backup'

    @openerpweb.httprequest
    def restore(self, req, db_file, restore_pwd, new_db):
        try:
            data = base64.encodestring(db_file.file.read())
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

class Session(openerpweb.Controller):
    _cp_path = "/base/session"

    @openerpweb.jsonrequest
    def login(self, req, db, login, password):
        req.session.login(db, login, password)
        ctx = req.session.get_context()

        return {
            "session_id": req.session_id,
            "uid": req.session._uid,
            "context": ctx
        }
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
        except:
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
        # TODO query server for installed web modules
        mods = []
        for name, manifest in openerpweb.addons_manifest.items():
            if name != 'base' and manifest.get('active', True):
                mods.append(name)
        return mods

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
                                                  openerpweb.nonliterals.CompoundContext(*(contexts or [])),
                                                  openerpweb.nonliterals.CompoundDomain(*(domains or [])))

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
            del saved_actions["actions"][min(saved_actions["actions"].keys())]
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

def clean_action(req, action):
    action.setdefault('flags', {})
    if action['type'] != 'ir.actions.act_window':
        return action

    context = req.session.eval_context(req.context)
    eval_ctx = req.session.evaluation_context(context)

    # values come from the server, we can just eval them
    if isinstance(action.get('context'), basestring):
        action['context'] = eval( action['context'], eval_ctx ) or {}

    if isinstance(action.get('domain'), basestring):
        action['domain'] = eval( action['domain'], eval_ctx ) or []

    return fix_view_modes(action)

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
    view_id = action.get('view_id', False)
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
    if 'views' not in action:
        generate_views(action)

    if action.pop('view_type') != 'form':
        return action

    action['views'] = [
        [id, mode if mode != 'tree' else 'list']
        for id, mode in action['views']
    ]

    return action

class Menu(openerpweb.Controller):
    _cp_path = "/base/menu"

    @openerpweb.jsonrequest
    def load(self, req):
        return {'data': self.do_load(req)}

    def do_load(self, req):
        """ Loads all menu items (all applications and their sub-menus).

        :param req: A request object, with an OpenERP session attribute
        :type req: < session -> OpenERPSession >
        :return: the menu root
        :rtype: dict('children': menu_nodes)
        """
        Menus = req.session.model('ir.ui.menu')
        # menus are loaded fully unlike a regular tree view, cause there are
        # less than 512 items
        context = req.session.eval_context(req.context)
        menu_ids = Menus.search([], 0, False, False, context)
        menu_items = Menus.read(menu_ids, ['name', 'sequence', 'parent_id'], context)
        menu_root = {'id': False, 'name': 'root', 'parent_id': [-1, '']}
        menu_items.append(menu_root)

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
                key=lambda x:x["sequence"])

        return menu_root

    @openerpweb.jsonrequest
    def action(self, req, menu_id):
        actions = load_actions_from_ir_values(req,'action', 'tree_but_open',
                                             [('ir.ui.menu', menu_id)], False)
        return {"action": actions}

class DataSet(openerpweb.Controller):
    _cp_path = "/base/dataset"

    @openerpweb.jsonrequest
    def fields(self, req, model):
        return {'fields': req.session.model(model).fields_get(False,
                                                              req.session.eval_context(req.context))}

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

        ids = Model.search(domain, 0, False, sort or False, context)
        # need to fill the dataset with all ids for the (domain, context) pair,
        # so search un-paginated and paginate manually before reading
        paginated_ids = ids[offset:(offset + limit if limit else None)]
        if fields and fields == ['id']:
            # shortcut read if we only want the ids
            return {
                'ids': ids,
                'records': map(lambda id: {'id': id}, paginated_ids)
            }

        records = Model.read(paginated_ids, fields or False, context)
        records.sort(key=lambda obj: ids.index(obj['id']))
        return {
            'ids': ids,
            'records': records
        }


    @openerpweb.jsonrequest
    def read(self, req, model, ids, fields=False):
        return self.do_search_read(req, model, ids, fields)

    @openerpweb.jsonrequest
    def get(self, req, model, ids, fields=False):
        return self.do_get(req, model, ids, fields)

    def do_get(self, req, model, ids, fields=False):
        """ Fetches and returns the records of the model ``model`` whose ids
        are in ``ids``.

        The results are in the same order as the inputs, but elements may be
        missing (if there is no record left for the id)

        :param req: the JSON-RPC2 request object
        :type req: openerpweb.JsonRequest
        :param model: the model to read from
        :type model: str
        :param ids: a list of identifiers
        :type ids: list
        :param fields: a list of fields to fetch, ``False`` or empty to fetch
                       all fields in the model
        :type fields: list | False
        :returns: a list of records, in the same order as the list of ids
        :rtype: list
        """
        Model = req.session.model(model)
        records = Model.read(ids, fields, req.session.eval_context(req.context))

        record_map = dict((record['id'], record) for record in records)

        return [record_map[id] for id in ids if record_map.get(id)]

    @openerpweb.jsonrequest
    def load(self, req, model, id, fields):
        m = req.session.model(model)
        value = {}
        r = m.read([id], False, req.session.eval_context(req.context))
        if r:
            value = r[0]
        return {'value': value}

    @openerpweb.jsonrequest
    def create(self, req, model, data):
        m = req.session.model(model)
        r = m.create(data, req.session.eval_context(req.context))
        return {'result': r}

    @openerpweb.jsonrequest
    def save(self, req, model, id, data):
        m = req.session.model(model)
        r = m.write([id], data, req.session.eval_context(req.context))
        return {'result': r}

    @openerpweb.jsonrequest
    def unlink(self, req, model, ids=()):
        Model = req.session.model(model)
        return Model.unlink(ids, req.session.eval_context(req.context))

    def call_common(self, req, model, method, args, domain_id=None, context_id=None):
        domain = args[domain_id] if domain_id and len(args) - 1 >= domain_id  else []
        context = args[context_id] if context_id and len(args) - 1 >= context_id  else {}
        c, d = eval_context_and_domain(req.session, context, domain)
        if domain_id and len(args) - 1 >= domain_id:
            args[domain_id] = d
        if context_id and len(args) - 1 >= context_id:
            args[context_id] = c

        return getattr(req.session.model(model), method)(*args)

    @openerpweb.jsonrequest
    def call(self, req, model, method, args, domain_id=None, context_id=None):
        return self.call_common(req, model, method, args, domain_id, context_id)

    @openerpweb.jsonrequest
    def call_button(self, req, model, method, args, domain_id=None, context_id=None):
        action = self.call_common(req, model, method, args, domain_id, context_id)
        if isinstance(action, dict) and action.get('type') != '':
            return {'result': clean_action(req, action)}
        return {'result': False}

    @openerpweb.jsonrequest
    def exec_workflow(self, req, model, id, signal):
        r = req.session.exec_workflow(model, id, signal)
        return {'result': r}

    @openerpweb.jsonrequest
    def default_get(self, req, model, fields):
        Model = req.session.model(model)
        return Model.default_get(fields, req.session.eval_context(req.context))

    @openerpweb.jsonrequest
    def name_search(self, req, model, search_str, domain=[], context={}):
        m = req.session.model(model)
        r = m.name_search(search_str+'%', domain, '=ilike', context)
        return {'result': r}

class DataGroup(openerpweb.Controller):
    _cp_path = "/base/group"
    @openerpweb.jsonrequest
    def read(self, req, model, fields, group_by_fields, domain=None, sort=None):
        Model = req.session.model(model)
        context, domain = eval_context_and_domain(req.session, req.context, domain)

        return Model.read_group(
            domain or [], fields, group_by_fields, 0, False,
            dict(context, group_by=group_by_fields), sort or False)

class View(openerpweb.Controller):
    _cp_path = "/base/view"

    def fields_view_get(self, req, model, view_id, view_type,
                        transform=True, toolbar=False, submenu=False):
        Model = req.session.model(model)
        context = req.session.eval_context(req.context)
        fvg = Model.fields_view_get(view_id, view_type, context, toolbar, submenu)
        # todo fme?: check that we should pass the evaluated context here
        self.process_view(req.session, fvg, context, transform)
        return fvg

    def process_view(self, session, fvg, context, transform):
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

        if transform:
            evaluation_context = session.evaluation_context(context or {})
            xml = self.transform_view(arch, session, evaluation_context)
        else:
            xml = ElementTree.fromstring(arch)
        fvg['arch'] = Xml2Json.convert_element(xml)

        for field in fvg['fields'].itervalues():
            if field.get('views'):
                for view in field["views"].itervalues():
                    self.process_view(session, view, None, transform)
            if field.get('domain'):
                field["domain"] = self.parse_domain(field["domain"], session)
            if field.get('context'):
                field["context"] = self.parse_context(field["context"], session)

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

    def parse_domain(self, domain, session):
        """ Parses an arbitrary string containing a domain, transforms it
        to either a literal domain or a :class:`openerpweb.nonliterals.Domain`

        :param domain: the domain to parse, if the domain is not a string it
                       is assumed to be a literal domain and is returned as-is
        :param session: Current OpenERP session
        :type session: openerpweb.openerpweb.OpenERPSession
        """
        if not isinstance(domain, (str, unicode)):
            return domain
        try:
            return openerpweb.ast.literal_eval(domain)
        except ValueError:
            # not a literal
            return openerpweb.nonliterals.Domain(session, domain)

    def parse_context(self, context, session):
        """ Parses an arbitrary string containing a context, transforms it
        to either a literal context or a :class:`openerpweb.nonliterals.Context`

        :param context: the context to parse, if the context is not a string it
               is assumed to be a literal domain and is returned as-is
        :param session: Current OpenERP session
        :type session: openerpweb.openerpweb.OpenERPSession
        """
        if not isinstance(context, (str, unicode)):
            return context
        try:
            return openerpweb.ast.literal_eval(context)
        except ValueError:
            return openerpweb.nonliterals.Context(session, context)

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
                elem.set(el, self.parse_domain(domain, session))
        for el in ['context', 'default_get']:
            context_string = elem.get(el, '').strip()
            if context_string:
                elem.set(el, self.parse_context(context_string, session))

class FormView(View):
    _cp_path = "/base/formview"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id, toolbar=False):
        fields_view = self.fields_view_get(req, model, view_id, 'form', toolbar=toolbar)
        return {'fields_view': fields_view}

class ListView(View):
    _cp_path = "/base/listview"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id, toolbar=False):
        fields_view = self.fields_view_get(req, model, view_id, 'tree', toolbar=toolbar)
        return {'fields_view': fields_view}

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

class SearchView(View):
    _cp_path = "/base/searchview"

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
                field["domain"] = self.parse_domain(field["domain"], req.session)
            if field.get('context'):
                field["context"] = self.parse_domain(field["context"], req.session)
        return {'fields': fields}

    @openerpweb.jsonrequest
    def get_filters(self, req, model):
        Model = req.session.model("ir.filters")
        filters = Model.get_filters(model)
        for filter in filters:
            filter["context"] = req.session.eval_context(self.parse_context(filter["context"], req.session))
            filter["domain"] = req.session.eval_domain(self.parse_domain(filter["domain"], req.session))
        return filters

    @openerpweb.jsonrequest
    def save_filter(self, req, model, name, context_to_save, domain):
        Model = req.session.model("ir.filters")
        ctx = openerpweb.nonliterals.CompoundContext(context_to_save)
        ctx.session = req.session
        ctx = ctx.evaluate()
        domain = openerpweb.nonliterals.CompoundDomain(domain)
        domain.session = req.session
        domain = domain.evaluate()
        uid = req.session._uid
        context = req.session.eval_context(req.context)
        to_return = Model.create_or_replace({"context": ctx,
                                             "domain": domain,
                                             "model_id": model,
                                             "name": name,
                                             "user_id": uid
                                             }, context)
        return to_return

class Binary(openerpweb.Controller):
    _cp_path = "/base/binary"

    @openerpweb.httprequest
    def image(self, req, model, id, field, **kw):
        req.httpresponse.headers['Content-Type'] = 'image/png'
        Model = req.session.model(model)
        context = req.session.eval_context(req.context)
        try:
            if not id:
                res = Model.default_get([field], context).get(field, '')
            else:
                res = Model.read([int(id)], [field], context)[0].get(field, '')
            return base64.decodestring(res)
        except: # TODO: what's the exception here?
            return self.placeholder()
    def placeholder(self):
        return open(os.path.join(openerpweb.path_addons, 'base', 'static', 'src', 'img', 'placeholder.png'), 'rb').read()

    @openerpweb.httprequest
    def saveas(self, req, model, id, field, fieldname, **kw):
        Model = req.session.model(model)
        context = req.session.eval_context(req.context)
        res = Model.read([int(id)], [field, fieldname], context)[0]
        filecontent = res.get(field, '')
        if not filecontent:
            raise cherrypy.NotFound
        else:
            req.httpresponse.headers['Content-Type'] = 'application/octet-stream'
            filename = '%s_%s' % (model.replace('.', '_'), id)
            if fieldname:
                filename = res.get(fieldname, '') or filename
            req.httpresponse.headers['Content-Disposition'] = 'attachment; filename=' +  filename
            return base64.decodestring(filecontent)

    @openerpweb.httprequest
    def upload(self, req, callback, ufile=None):
        cherrypy.response.timeout = 500
        headers = {}
        for key, val in req.httprequest.headers.iteritems():
            headers[key.lower()] = val
        size = int(headers.get('content-length', 0))
        # TODO: might be useful to have a configuration flag for max-length file uploads
        try:
            out = """<script language="javascript" type="text/javascript">
                        var win = window.top.window,
                            callback = win[%s];
                        if (typeof(callback) === 'function') {
                            callback.apply(this, %s);
                        } else {
                            win.jQuery('#oe_notification', win.document).notify('create', {
                                title: "Ajax File Upload",
                                text: "Could not find callback"
                            });
                        }
                    </script>"""
            data = ufile.file.read()
            args = [size, ufile.filename, ufile.headers.getheader('Content-Type'), base64.encodestring(data)]
        except Exception, e:
            args = [False, e.message]
        return out % (simplejson.dumps(callback), simplejson.dumps(args))

    @openerpweb.httprequest
    def upload_attachment(self, req, callback, model, id, ufile=None):
        cherrypy.response.timeout = 500
        context = req.session.eval_context(req.context)
        Model = req.session.model('ir.attachment')
        try:
            out = """<script language="javascript" type="text/javascript">
                        var win = window.top.window,
                            callback = win[%s];
                        if (typeof(callback) === 'function') {
                            callback.call(this, %s);
                        }
                    </script>"""
            attachment_id = Model.create({
                'name': ufile.filename,
                'datas': base64.encodestring(ufile.file.read()),
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
    _cp_path = "/base/action"

    @openerpweb.jsonrequest
    def load(self, req, action_id):
        Actions = req.session.model('ir.actions.actions')
        value = False
        context = req.session.eval_context(req.context)
        action_type = Actions.read([action_id], ['type'], context)
        if action_type:
            action = req.session.model(action_type[0]['type']).read([action_id], False,
                                                                    context)
            if action:
                value = clean_action(req, action[0])
        return {'result': value}

    @openerpweb.jsonrequest
    def run(self, req, action_id):
        return clean_action(req, req.session.model('ir.actions.server').run(
            [action_id], req.session.eval_context(req.context)))

class TreeView(View):
    _cp_path = "/base/treeview"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id, toolbar=False):
        return self.fields_view_get(req, model, view_id, 'tree', toolbar=toolbar)

    @openerpweb.jsonrequest
    def action(self, req, model, id):
        return load_actions_from_ir_values(
            req,'action', 'tree_but_open',[(model, id)],
            False)

def export_csv(fields, result):
    fp = StringIO()
    writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

    writer.writerow(fields)

    for data in result:
        row = []
        for d in data:
            if isinstance(d, basestring):
                d = d.replace('\n',' ').replace('\t',' ')
                try:
                    d = d.encode('utf-8')
                except:
                    pass
            if d is False: d = None
            row.append(d)
        writer.writerow(row)

    fp.seek(0)
    data = fp.read()
    fp.close()
    return data

def export_xls(fieldnames, table):
    try:
        import xlwt
    except ImportError:
        common.error(_('Import Error.'), _('Please install xlwt library to export to MS Excel.'))

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')

    for i, fieldname in enumerate(fieldnames):
        worksheet.write(0, i, str(fieldname))
        worksheet.col(i).width = 8000 # around 220 pixels

    style = xlwt.easyxf('align: wrap yes')

    for row_index, row in enumerate(table):
        for cell_index, cell_value in enumerate(row):
            cell_value = str(cell_value)
            cell_value = re.sub("\r", " ", cell_value)
            worksheet.write(row_index + 1, cell_index, cell_value, style)


    fp = StringIO()
    workbook.save(fp)
    fp.seek(0)
    data = fp.read()
    fp.close()
    #return data.decode('ISO-8859-1')
    return unicode(data, 'utf-8', 'replace')

class Export(View):
    _cp_path = "/base/export"

    def fields_get(self, req, model):
        Model = req.session.model(model)
        fields = Model.fields_get(False, req.session.eval_context(req.context))
        return fields

    @openerpweb.jsonrequest
    def get_fields(self, req, model, prefix='', name= '', field_parent=None, params={}):
        import_compat = params.get("import_compat", False)

        fields = self.fields_get(req, model)
        field_parent_type = params.get("parent_field_type",False)

        if import_compat and field_parent_type and field_parent_type == "many2one":
            fields = {}

        fields.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})
        records = []
        fields_order = fields.keys()
        fields_order.sort(lambda x,y: -cmp(fields[x].get('string', ''), fields[y].get('string', '')))

        for index, field in enumerate(fields_order):
            value = fields[field]
            record = {}
            if import_compat and value.get('readonly', False):
                ok = False
                for sl in value.get('states', {}).values():
                    for s in sl:
                        ok = ok or (s==['readonly',False])
                if not ok: continue

            id = prefix + (prefix and '/'or '') + field
            nm = name + (name and '/' or '') + value['string']
            record.update(id=id, string= nm, action='javascript: void(0)',
                          target=None, icon=None, children=[], field_type=value.get('type',False), required=value.get('required', False))
            records.append(record)

            if len(nm.split('/')) < 3 and value.get('relation', False):
                if import_compat:
                    ref = value.pop('relation')
                    cfields = self.fields_get(req, ref)
                    if (value['type'] == 'many2many'):
                        record['children'] = []
                        record['params'] = {'model': ref, 'prefix': id, 'name': nm}

                    elif value['type'] == 'many2one':
                        record['children'] = [id + '/id', id + '/.id']
                        record['params'] = {'model': ref, 'prefix': id, 'name': nm}

                    else:
                        cfields_order = cfields.keys()
                        cfields_order.sort(lambda x,y: -cmp(cfields[x].get('string', ''), cfields[y].get('string', '')))
                        children = []
                        for j, fld in enumerate(cfields_order):
                            cid = id + '/' + fld
                            cid = cid.replace(' ', '_')
                            children.append(cid)
                        record['children'] = children or []
                        record['params'] = {'model': ref, 'prefix': id, 'name': nm}
                else:
                    ref = value.pop('relation')
                    cfields = self.fields_get(req, ref)
                    cfields_order = cfields.keys()
                    cfields_order.sort(lambda x,y: -cmp(cfields[x].get('string', ''), cfields[y].get('string', '')))
                    children = []
                    for j, fld in enumerate(cfields_order):
                        cid = id + '/' + fld
                        cid = cid.replace(' ', '_')
                        children.append(cid)
                    record['children'] = children or []
                    record['params'] = {'model': ref, 'prefix': id, 'name': nm}

        records.reverse()
        return records

    @openerpweb.jsonrequest
    def save_export_lists(self, req, name, model, field_list):
        result = {'resource':model, 'name':name, 'export_fields': []}
        for field in field_list:
            result['export_fields'].append((0, 0, {'name': field}))
        return req.session.model("ir.exports").create(result, req.session.eval_context(req.context))

    @openerpweb.jsonrequest
    def exist_export_lists(self, req, model):
        export_model = req.session.model("ir.exports")
        return export_model.read(export_model.search([('resource', '=', model)]), ['name'])

    @openerpweb.jsonrequest
    def delete_export(self, req, export_id):
        req.session.model("ir.exports").unlink(export_id, req.session.eval_context(req.context))
        return True

    @openerpweb.jsonrequest
    def namelist(self,req,  model, export_id):

        result = self.get_data(req, model, req.session.eval_context(req.context))
        ir_export_obj = req.session.model("ir.exports")
        ir_export_line_obj = req.session.model("ir.exports.line")

        field = ir_export_obj.read(export_id)
        fields = ir_export_line_obj.read(field['export_fields'])

        name_list = {}
        [name_list.update({field['name']: result.get(field['name'])}) for field in fields]
        return name_list

    def get_data(self, req, model, context=None):
        ids = []
        context = context or {}
        fields_data = {}
        proxy = req.session.model(model)
        fields = self.fields_get(req, model)
        if not ids:
            f1 = proxy.fields_view_get(False, 'tree', context)['fields']
            f2 = proxy.fields_view_get(False, 'form', context)['fields']

            fields = dict(f1)
            fields.update(f2)
            fields.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})

        def rec(fields):
            _fields = {'id': 'ID' , '.id': 'Database ID' }
            def model_populate(fields, prefix_node='', prefix=None, prefix_value='', level=2):
                fields_order = fields.keys()
                fields_order.sort(lambda x,y: -cmp(fields[x].get('string', ''), fields[y].get('string', '')))

                for field in fields_order:
                    fields_data[prefix_node+field] = fields[field]
                    if prefix_node:
                        fields_data[prefix_node + field]['string'] = '%s%s' % (prefix_value, fields_data[prefix_node + field]['string'])
                    st_name = fields[field]['string'] or field
                    _fields[prefix_node+field] = st_name
                    if fields[field].get('relation', False) and level>0:
                        fields2 = self.fields_get(req,  fields[field]['relation'])
                        fields2.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})
                        model_populate(fields2, prefix_node+field+'/', None, st_name+'/', level-1)
            model_populate(fields)
            return _fields
        return rec(fields)

    @openerpweb.jsonrequest
    def export_data(self, req, model, fields, ids, domain, import_compat=False, export_format="csv", context=None):
        context = req.session.eval_context(req.context)
        modle_obj = req.session.model(model)

        ids = ids or modle_obj.search(domain, context=context)

        field = fields.keys()
        result = modle_obj.export_data(ids, field , context).get('datas',[])

        if not import_compat:
            field = [val.strip() for val in fields.values()]

        if export_format == 'xls':
            return export_xls(field, result)
        else:
            return export_csv(field, result)

class Export(View):
    _cp_path = "/base/report"

    @openerpweb.jsonrequest
    def get_report(self, req, action):
        report_srv = req.session.proxy("report")
        context = req.session.eval_context(openerpweb.nonliterals.CompoundContext(req.context, \
                                                                                  action["context"]))

        args = [req.session._db, req.session._uid, req.session._password, action["report_name"], context["active_ids"], {"id": context["active_id"], "model": context["active_model"], "report_type": action["report_type"]}, context]
        report_id = report_srv.report(*args)
        report = None
        while True:
            args2 = [req.session._db, req.session._uid, req.session._password, report_id]
            report = report_srv.report_get(*args2)
            if report["state"]:
                break

            time.sleep(_REPORT_POLLER_DELAY)
        #TODO: ok now we've got the report, and so what?
        return False

class Import(View):
    _cp_path = "/base/import"

    def fields_get(self, req, model):
        Model = req.session.model(model)
        fields = Model.fields_get(False, req.session.eval_context(req.context))
        return fields

    @openerpweb.httprequest
    def detect_data(self, req, **params):
        import StringIO
        _fields = {}
        _fields_invert = {}
        req_field = []
        error = None
        all_fields = []
        fields = dict(req.session.model(params.get('model')).fields_get(False, req.session.eval_context(req.context)))
        fields.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})

        for field in fields:
            value = fields[field]
            if (value.get('required',False) == True):
                req_field.append(field)

        def model_populate(fields, prefix_node='', prefix=None, prefix_value='', level=2):
            def str_comp(x,y):
                if x<y: return 1
                elif x>y: return -1
                else: return 0

            fields_order = fields.keys()
            fields_order.sort(lambda x,y: str_comp(fields[x].get('string', ''), fields[y].get('string', '')))
            for field in fields_order:
                if (fields[field].get('type','') not in ('reference',))\
                            and (not fields[field].get('readonly')\
                            or not dict(fields[field].get('states', {}).get(
                            'draft', [('readonly', True)])).get('readonly',True)):

                    st_name = prefix_value+fields[field]['string'] or field
                    _fields[prefix_node+field] = st_name
                    _fields_invert[st_name] = prefix_node+field

                    if fields[field].get('type','')=='one2many' and level>0:
                        fields2 = self.fields_get(req,  fields[field]['relation'])
                        model_populate(fields2, prefix_node+field+'/', None, st_name+'/', level-1)

                    if fields[field].get('relation',False) and level>0:
                        model_populate({'/id': {'type': 'char', 'string': 'ID'}, '.id': {'type': 'char', 'string': 'Database ID'}},
                                       prefix_node+field, None, st_name+'/', level-1)
        fields.update({'id':{'string':'ID'},'.id':{'string':'Database ID'}})
        model_populate(fields)
        all_fields = fields.keys()

        try:
            data = csv.reader(params.get('csvfile').file, quotechar=str(params.get('csvdel')), delimiter=str(params.get('csvsep')))
        except:
            error={'message': 'error opening .CSV file. Input Error.'}
            return simplejson.dumps({'error':error})

        records = []
        fields = []
        word=''
        limit = 4
        count = 0
        try:
            for i, row in enumerate(data):
                records.append(row)
                if i == limit:
                    break

            for j, line in enumerate(records):
                if j == 1:
                    break
                for word in line:
                    word = str(word.decode(params.get('csvcode')))
                    if word in _fields:
                        fields.append((word, _fields[word]))
                    elif word in _fields_invert.keys():
                        fields.append((_fields_invert[word], word))
                    else:
                        count = count + 1
                        fields.append((word, word))

            if len(line) == count:
                error = {'message':"File has not any column header."}
        except:
            error = {'message':('Error processing the first line of the file. Field "%s" is unknown') % (word,)}

        if error:
            params.get('csvfile').file.seek(0)
            error=dict(error, preview=params.get('csvfile').file.read(200))
            return simplejson.dumps({'error':error})

        return simplejson.dumps({'records':records[1:],'header':fields,'all_fields':all_fields,'req_field':req_field})

    @openerpweb.httprequest
    def import_data(self, req, **params):
        import StringIO
        _fields = {}
        _fields_invert = {}
        prefix_node=''
        prefix_value = ''

        context = req.session.eval_context(req.context)
        modle_obj = req.session.model(params.get('model'))
        res = None
        content = params.get('csvfile').file.read()
        input=StringIO.StringIO(content)
        limit = 0
        data = []

        if not (params.get('csvdel') and len(params.get('csvdel')) == 1):
            error={'message': "The CSV delimiter must be a single character"}
            return simplejson.dumps({'error':error})

        try:
            for j, line in enumerate(csv.reader(input, quotechar=str(params.get('csvdel')), delimiter=str(params.get('csvsep')))):
                # If the line contains no data, we should skip it.
                if not line:
                    continue
                if j == limit:
                    fields = line
                else:
                    data.append(line)
        except csv.Error, e:
            error={'message': str(e),'title': 'File Format Error'}
            return simplejson.dumps({'error':error})

        datas = []
        ctx = context

        if not isinstance(fields, list):
            fields = [fields]

        flds = dict(req.session.model(params.get('model')).fields_get(False, req.session.eval_context(req.context)))
        flds.update({'id':{'string':'ID'},'.id':{'string':'Database ID'}})
        fields_order = flds.keys()
        for field in fields_order:
            st_name = prefix_value+flds[field]['string'] or field
            _fields[prefix_node+field] = st_name
            _fields_invert[st_name] = prefix_node+field

        unmatch_field = []
        for fld in fields:
            if ((fld not in _fields.keys()) and (fld not in _fields_invert.keys())):
                unmatch_field.append(fld)

        if unmatch_field:
            error = {'message':("You cannot import the fields '%s',because we cannot auto-detect it." % (unmatch_field))}
            return simplejson.dumps({'error':error})

        for line in data:
            try:
                datas.append(map(lambda x:x.decode(params.get('csvcode')).encode('utf-8'), line))
            except:
                datas.append(map(lambda x:x.decode('latin').encode('utf-8'), line))

        # If the file contains nothing,
        if not datas:
            error = {'message': 'The file is empty !', 'title': 'Importation !'}
            return simplejson.dumps({'error':error})

        #Inverting the header into column names
        try:
            res = modle_obj.import_data(fields, datas, 'init', '', False, ctx)
        except xmlrpclib.Fault, e:
            error = {"message":e.faultCode}
            return simplejson.dumps({'error':error})

        if res[0]>=0:
            success={'message':'Imported %d objects' % (res[0],)}
            return simplejson.dumps({'success':success})

        d = ''
        for key,val in res[1].items():
            d+= ('%s: %s' % (str(key),str(val)))
        msg = 'Error trying to import this record:%s. ErrorMessage:%s %s' % (d,res[2],res[3])
        error = {'message':str(msg), 'title':'ImportationError'}
        return simplejson.dumps({'error':error})
