# -*- coding: utf-8 -*-

import base64
import csv
import glob
import itertools
import operator
import os
import re
import simplejson
import textwrap
import xmlrpclib
import time
import zlib
from xml.etree import ElementTree
from cStringIO import StringIO

from babel.messages.pofile import read_po

import web.common.dispatch as openerpweb
import web.common.ast
import web.common.nonliterals
import web.common.release
openerpweb.ast = web.common.ast
openerpweb.nonliterals = web.common.nonliterals


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
# OpenERP Web web Controllers
#----------------------------------------------------------

def manifest_glob(addons_path, addons, key):
    files = []
    for addon in addons:
        globlist = openerpweb.addons_manifest.get(addon, {}).get(key, [])
        for pattern in globlist:
            for path in glob.glob(os.path.join(addons_path, addon, pattern)):
                files.append(path[len(addons_path):])
    return files

def concat_files(addons_path, file_list):
    """ Concatenate file content
    return (concat,timestamp)
    concat: concatenation of file content
    timestamp: max(os.path.getmtime of file_list)
    """
    files_content = []
    files_timestamp = 0
    for i in file_list:
        fname = os.path.join(addons_path, i[1:])
        ftime = os.path.getmtime(fname)
        if ftime > files_timestamp:
            files_timestamp = ftime
        files_content.append(open(fname).read())
    files_concat = "".join(files_content)
    return files_concat,files_timestamp

home_template = textwrap.dedent("""<!DOCTYPE html>
<html style="height: 100%%">
    <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8" />
        <title>OpenERP</title>
        <link rel="shortcut icon" href="/web/static/src/img/favicon.ico" type="image/x-icon"/>
        %(css)s
        %(javascript)s
        <script type="text/javascript">
            $(function() {
                var c = new openerp.init();
                var wc = new c.web.WebClient("oe");
                wc.start();
            });
        </script>
    </head>
    <body id="oe" class="openerp"></body>
</html>
""")
class WebClient(openerpweb.Controller):
    _cp_path = "/web/webclient"

    @openerpweb.jsonrequest
    def csslist(self, req, mods='web'):
        return manifest_glob(req.config.addons_path, mods.split(','), 'css')

    @openerpweb.jsonrequest
    def jslist(self, req, mods='web'):
        return manifest_glob(req.config.addons_path, mods.split(','), 'js')

    @openerpweb.httprequest
    def css(self, req, mods='web'):
        files = manifest_glob(req.config.addons_path, mods.split(','), 'css')
        content,timestamp = concat_files(req.config.addons_path, files)
        # TODO request set the Date of last modif and Etag
        return req.make_response(content, [('Content-Type', 'text/css')])

    @openerpweb.httprequest
    def js(self, req, mods='web'):
        files = manifest_glob(req.config.addons_path, mods.split(','), 'js')
        content,timestamp = concat_files(req.config.addons_path, files)
        # TODO request set the Date of last modif and Etag
        return req.make_response(content, [('Content-Type', 'application/javascript')])

    @openerpweb.httprequest
    def home(self, req, s_action=None, **kw):
        # script tags
        jslist = ['/web/webclient/js']
        if req.debug:
            jslist = [i + '?debug=' + str(time.time()) for i in manifest_glob(req.config.addons_path, ['web'], 'js')]
        js = "\n        ".join(['<script type="text/javascript" src="%s"></script>'%i for i in jslist])

        # css tags
        csslist = ['/web/webclient/css']
        if req.debug:
            csslist = [i + '?debug=' + str(time.time()) for i in manifest_glob(req.config.addons_path, ['web'], 'css')]
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
                f_name = os.path.join(req.config.addons_path, addon_name, "po", l + ".po")
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

    @openerpweb.jsonrequest
    def version_info(self, req):
        return {
            "version": web.common.release.version
        }

class Database(openerpweb.Controller):
    _cp_path = "/web/database"

    @openerpweb.jsonrequest
    def get_list(self, req):
        proxy = req.session.proxy("db")
        dbs = proxy.list()
        h = req.httprequest.headers['Host'].split(':')[0]
        d = h.split('.')[0]
        r = req.config.dbfilter.replace('%h', h).replace('%d', d)
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
            db_dump = base64.b64decode(
                req.session.proxy("db").dump(backup_pwd, backup_db))
            return req.make_response(db_dump,
                [('Content-Type', 'application/octet-stream; charset=binary'),
                 ('Content-Disposition', 'attachment; filename="' + backup_db + '.dump"')],
                {'fileToken': int(token)}
            )
        except xmlrpclib.Fault, e:
            if e.faultCode and e.faultCode.split(':')[0] == 'AccessDenied':
                return 'Backup Database|' + e.faultCode
        return 'Backup Database|Could not generate database backup'

    @openerpweb.httprequest
    def restore(self, req, db_file, restore_pwd, new_db):
        try:
            data = base64.b64encode(db_file.file.read())
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
    _cp_path = "/web/session"

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
            if name != 'web' and manifest.get('active', True):
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

    context = req.session.eval_context(req.context)
    eval_ctx = req.session.evaluation_context(context)

    # values come from the server, we can just eval them
    if isinstance(action.get('context'), basestring):
        action['context'] = eval( action['context'], eval_ctx ) or {}

    if isinstance(action.get('domain'), basestring):
        action['domain'] = eval( action['domain'], eval_ctx ) or []

    if action['type'] == 'ir.actions.act_window':
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
    _cp_path = "/web/menu"

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
    _cp_path = "/web/dataset"

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

        for i in xrange(len(args)):
            if isinstance(args[i], web.common.nonliterals.BaseContext):
                args[i] = req.session.eval_context(args[i])
            if isinstance(args[i], web.common.nonliterals.BaseDomain):
                args[i] = req.session.eval_domain(args[i])

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
        self.process_view(req.session, fvg, context, transform)
        if toolbar and transform:
            self.process_toolbar(req, fvg['toolbar'])
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

    def process_toolbar(self, req, toolbar):
        """
        The toolbar is a mapping of section_key: [action_descriptor]

        We need to clean all those actions in order to ensure correct
        round-tripping
        """
        for actions in toolbar.itervalues():
            for action in actions:
                if 'context' in action:
                    action['context'] = self.parse_context(
                        action['context'], req.session)
                if 'domain' in action:
                    action['domain'] = self.parse_domain(
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

    @openerpweb.jsonrequest
    def load(self, req, model, view_id, view_type, toolbar=False):
        return self.fields_view_get(req, model, view_id, view_type, toolbar=toolbar)

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
    _cp_path = "/web/binary"

    @openerpweb.httprequest
    def image(self, req, model, id, field, **kw):
        Model = req.session.model(model)
        context = req.session.eval_context(req.context)

        try:
            if not id:
                res = Model.default_get([field], context).get(field, '')
            else:
                res = Model.read([int(id)], [field], context)[0].get(field, '')
            image_data = base64.b64decode(res)
        except (TypeError, xmlrpclib.Fault):
            image_data = self.placeholder(req)
        return req.make_response(image_data, [
            ('Content-Type', 'image/png'), ('Content-Length', len(image_data))])
    def placeholder(self, req):
        return open(os.path.join(req.addons_path, 'web', 'static', 'src', 'img', 'placeholder.png'), 'rb').read()

    @openerpweb.httprequest
    def saveas(self, req, model, id, field, fieldname, **kw):
        Model = req.session.model(model)
        context = req.session.eval_context(req.context)
        res = Model.read([int(id)], [field, fieldname], context)[0]
        filecontent = res.get(field, '')
        if not filecontent:
            return req.not_found()
        else:
            filename = '%s_%s' % (model.replace('.', '_'), id)
            if fieldname:
                filename = res.get(fieldname, '') or filename
            return req.make_response(filecontent,
                [('Content-Type', 'application/octet-stream'),
                 ('Content-Disposition', 'attachment; filename=' +  filename)])

    @openerpweb.httprequest
    def upload(self, req, callback, ufile):
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
            data = ufile.read()
            args = [ufile.content_length, ufile.filename,
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
                        var win = window.top.window,
                            callback = win[%s];
                        if (typeof(callback) === 'function') {
                            callback.call(this, %s);
                        }
                    </script>"""
            attachment_id = Model.create({
                'name': ufile.filename,
                'datas': base64.encodestring(ufile.read()),
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

    @openerpweb.jsonrequest
    def load(self, req, action_id):
        Actions = req.session.model('ir.actions.actions')
        value = False
        context = req.session.eval_context(req.context)
        action_type = Actions.read([action_id], ['type'], context)
        if action_type:
            ctx = {}
            if action_type[0]['type'] == 'ir.actions.report.xml':
                ctx.update({'bin_size': True})
            ctx.update(context)
            action = req.session.model(action_type[0]['type']).read([action_id], False, ctx)
            if action:
                value = clean_action(req, action[0])
        return {'result': value}

    @openerpweb.jsonrequest
    def run(self, req, action_id):
        return clean_action(req, req.session.model('ir.actions.server').run(
            [action_id], req.session.eval_context(req.context)))

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
        ], key=operator.itemgetter(1))

    def fields_get(self, req, model):
        Model = req.session.model(model)
        fields = Model.fields_get(False, req.session.eval_context(req.context))
        return fields

    @openerpweb.jsonrequest
    def get_fields(self, req, model, prefix='', parent_name= '',
                   import_compat=True, parent_field_type=None):

        if import_compat and parent_field_type == "many2one":
            fields = {}
        else:
            fields = self.fields_get(req, model)
        fields['.id'] = fields.pop('id') if 'id' in fields else {'string': 'ID'}

        fields_sequence = sorted(fields.iteritems(),
            key=lambda field: field[1].get('string', ''))

        records = []
        for field_name, field in fields_sequence:
            if import_compat and field.get('readonly'):
                # If none of the field's states unsets readonly, skip the field
                if all(dict(attrs).get('readonly', True)
                       for attrs in field.get('states', {}).values()):
                    continue

            id = prefix + (prefix and '/'or '') + field_name
            name = parent_name + (parent_name and '/' or '') + field['string']
            record = {'id': id, 'string': name,
                      'value': id, 'children': False,
                      'field_type': field.get('type'),
                      'required': field.get('required')}
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
        fields['.id'] = fields.pop('id') if 'id' in fields else {'string': 'ID'}

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
        ids = ids or Model.search(domain, context=context)

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
    fmt = ('csv', 'CSV')

    @property
    def content_type(self):
        return 'text/csv;charset=utf8'

    def filename(self, base):
        return base + '.csv'

    def from_data(self, fields, rows):
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        writer.writerow(fields)

        for data in rows:
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

class ExcelExport(Export):
    _cp_path = '/web/export/xls'
    fmt = ('xls', 'Excel')

    @property
    def content_type(self):
        return 'application/vnd.ms-excel'

    def filename(self, base):
        return base + '.xls'

    def from_data(self, fields, rows):
        import xlwt

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')

        for i, fieldname in enumerate(fields):
            worksheet.write(0, i, str(fieldname))
            worksheet.col(i).width = 8000 # around 220 pixels

        style = xlwt.easyxf('align: wrap yes')

        for row_index, row in enumerate(rows):
            for cell_index, cell_value in enumerate(row):
                if isinstance(cell_value, basestring):
                    cell_value = re.sub("\r", " ", cell_value)
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
            openerpweb.nonliterals.CompoundContext(
                req.context or {}, action[ "context"]))

        report_data = {}
        report_ids = context["active_ids"]
        if 'report_type' in action:
            report_data['report_type'] = action['report_type']
        if 'datas' in action:
            if 'form' in action['datas']:
                report_data['form'] = action['datas']['form']
            if 'ids' in action['datas']:
                report_ids = action['datas']['ids']
        
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
        return req.make_response(report,
             headers=[
                 ('Content-Disposition', 'attachment; filename="%s.%s"' % (action['report_name'], report_struct['format'])),
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
    def detect_data(self, req, model, csvfile, csvsep, csvdel, csvcode, csvskip,
                    jsonp):

        _fields = {}
        _fields_invert = {}
        req_field = []
        error = None
        fields = req.session.model(model).fields_get(False, req.session.eval_context(req.context))
        fields.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})

        for field in fields:
            value = fields[field]
            if value.get('required'):
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

                    if fields[field].get('type')=='one2many' and level>0:
                        fields2 = self.fields_get(req,  fields[field]['relation'])
                        model_populate(fields2, prefix_node+field+'/', None, st_name+'/', level-1)

                    if fields[field].get('relation',False) and level>0:
                        model_populate({'/id': {'type': 'char', 'string': 'ID'}, '.id': {'type': 'char', 'string': 'Database ID'}},
                                       prefix_node+field, None, st_name+'/', level-1)
        fields.update({'id':{'string':'ID'},'.id':{'string':'Database ID'}})
        model_populate(fields)

        all_fields = fields.keys()
        all_fields.sort()

        try:
            data = csv.reader(csvfile, quotechar=str(csvdel), delimiter=str(csvsep))
        except:
            error={'message': 'error opening .CSV file. Input Error.'}
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error':error}))

        records = []
        count = 0
        header_fields = []
        word=''

        try:
            for rec in itertools.islice(data,0,4):
                records.append(rec)

            headers = itertools.islice(records,1)
            line = headers.next()

            for word in line:
                word = str(word.decode(csvcode))
                if word in _fields:
                    header_fields.append((word, _fields[word]))
                elif word in _fields_invert.keys():
                    header_fields.append((_fields_invert[word], word))
                else:
                    count = count + 1
                    header_fields.append((word, word))

            if len(line) == count:
                error = {'message':"File has not any column header."}
        except:
            error = {'message':('Error processing the first line of the file. Field "%s" is unknown') % (word,)}

        if error:
            csvfile.seek(0)
            error=dict(error, preview=csvfile.read(200))
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error':error}))

        return '<script>window.top.%s(%s);</script>' % (
            jsonp, simplejson.dumps({'records':records[1:],'header':header_fields,'all_fields':all_fields,'req_field':req_field}))

    @openerpweb.httprequest
    def import_data(self, req, model, csvfile, csvsep, csvdel, csvcode, csvskip,
                        jsonp):

        _fields = {}
        _fields_invert = {}
        prefix_node=''
        prefix_value = ''

        context = req.session.eval_context(req.context)
        modle_obj = req.session.model(model)
        res = None

        limit = 0
        data = []

        if not (csvdel and len(csvdel) == 1):
            error={'message': "The CSV delimiter must be a single character"}
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error':error}))

        try:
            data_record = csv.reader(csvfile, quotechar=str(csvdel), delimiter=str(csvsep))
            for rec in itertools.islice(data_record,0,None):
                data.append(rec)

            headers = itertools.islice(data,1)
            fields = headers.next()

        except csv.Error, e:
            error={'message': str(e),'title': 'File Format Error'}
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error':error}))

        datas = []
        ctx = context

        if not isinstance(fields, list):
            fields = [fields]

        flds = modle_obj.fields_get(False, req.session.eval_context(req.context))
        flds.update({'id':{'string':'ID'},'.id':{'string':'Database ID'}})
        fields_order = flds.keys()
        for field in fields_order:
            st_name = prefix_value+flds[field]['string'] or field
            _fields[prefix_node+field] = st_name
            _fields_invert[st_name] = prefix_node+field

        unmatch_field = []
        for fld in fields:
            if ((fld not in _fields) and (fld not in _fields_invert)):
                unmatch_field.append(fld)

        if unmatch_field:
            error = {'message':("You cannot import the fields '%s',because we cannot auto-detect it." % (unmatch_field))}
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error':error}))

        for line in data[1:]:
            try:
                datas.append(map(lambda x:x.decode(csvcode).encode('utf-8'), line))
            except:
                datas.append(map(lambda x:x.decode('latin').encode('utf-8'), line))

        # If the file contains nothing,
        if not datas:
            error = {'message': 'The file is empty !', 'title': 'Importation !'}
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error':error}))

        #Inverting the header into column names
        try:
            res = modle_obj.import_data(fields, datas, 'init', '', False, ctx)
        except xmlrpclib.Fault, e:
            error = {"message":e.faultCode}
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'error':error}))

        if res[0]>=0:
            return '<script>window.top.%s(%s);</script>' % (
                jsonp, simplejson.dumps({'success':True}))

        d = ''
        for key,val in res[1].items():
            d+= ('%s: %s' % (str(key),str(val)))
        msg = 'Error trying to import this record:%s. ErrorMessage:%s %s' % (d,res[2],res[3])
        error = {'message':str(msg), 'title':'ImportationError'}
        return '<script>window.top.%s(%s);</script>' % (
            jsonp, simplejson.dumps({'error':error}))
