# -*- coding: utf-8 -*-
import glob, os
from xml.etree import ElementTree
from cStringIO import StringIO

import simplejson

import openerpweb
import openerpweb.ast
import openerpweb.nonliterals

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

class Session(openerpweb.Controller):
    _cp_path = "/base/session"

    def manifest_glob(self, modlist, key):
        files = []
        for i in modlist:
            globlist = openerpweb.addons_manifest.get(i, {}).get(key, [])
            for j in globlist:
                for k in glob.glob(os.path.join(openerpweb.path_addons, i, j)):
                    files.append(k[len(openerpweb.path_addons):])
        return files

    def concat_files(self, file_list):
        """ Concatenate file content
        return (concat,timestamp)
        concat: concatenation of file content
        timestamp: max(os.path.getmtime of file_list)
        """
        root = openerpweb.path_root
        files_content = []
        files_timestamp = 0
        for i in file_list:
            fname = os.path.join(root, i)
            ftime = os.path.getmtime(fname)
            if ftime > files_timestamp:
                files_timestamp = ftime
            files_content = open(fname).read()
        files_concat = "".join(files_content)
        return files_concat

    @openerpweb.jsonrequest
    def login(self, req, db, login, password):
        req.session.login(db, login, password)

        return {
            "session_id": req.session_id,
            "uid": req.session._uid,
        }

    @openerpweb.jsonrequest
    def modules(self, req):
        return {"modules": ["base", "base_hello", "base_calendar", "base_gantt", "base_graph"]}

    @openerpweb.jsonrequest
    def csslist(self, req, mods='base,base_hello'):
        return {'files': self.manifest_glob(mods.split(','), 'css')}

    @openerpweb.jsonrequest
    def jslist(self, req, mods='base,base_hello'):
        return {'files': self.manifest_glob(mods.split(','), 'js')}

    def css(self, req, mods='base,base_hello'):
        files = self.manifest_glob(mods.split(','), 'css')
        concat = self.concat_files(files)[0]
        # TODO request set the Date of last modif and Etag
        return concat
    css.exposed = True

    def js(self, req, mods='base,base_hello'):
        files = self.manifest_glob(mods.split(','), 'js')
        concat = self.concat_files(files)[0]
        # TODO request set the Date of last modif and Etag
        return concat
    js.exposed = True

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
        context = req.session.eval_contexts(contexts)
        domain = req.session.eval_domains(domains, context)

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

def load_actions_from_ir_values(req, key, key2, models, meta, context):
    Values = req.session.model('ir.values')
    actions = Values.get(key, key2, models, meta, context)

    for _, _, action in actions:
        # values come from the server, we can just eval them
        if isinstance(action['context'], basestring):
            action['context'] = eval(
                action['context'],
                req.session.evaluation_context()) or {}

        if isinstance(action['domain'], basestring):
            action['domain'] = eval(
                action['domain'],
                req.session.evaluation_context(
                    action['context'])) or []
        fix_view_modes(action)
    return actions

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
    if action.pop('view_type') != 'form':
        return

    action['view_mode'] = ','.join(
        mode if mode != 'tree' else 'list'
        for mode in action['view_mode'].split(','))
    action['views'] = [
        [id, mode if mode != 'tree' else 'list']
        for id, mode in action['views']
    ]

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
        menu_ids = Menus.search([])
        menu_items = Menus.read(menu_ids, ['name', 'sequence', 'parent_id'])
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
                                             [('ir.ui.menu', menu_id)], False, {})

        return {"action": actions}

class DataSet(openerpweb.Controller):
    _cp_path = "/base/dataset"

    @openerpweb.jsonrequest
    def fields(self, req, model):
        return {'fields': req.session.model(model).fields_get()}

    @openerpweb.jsonrequest
    def search_read(self, request, model, fields=False, offset=0, limit=False, domain=None, context=None, sort=None):
        return self.do_search_read(request, model, fields, offset, limit, domain, context, sort)
    def do_search_read(self, request, model, fields=False, offset=0, limit=False, domain=None, context=None, sort=None):
        """ Performs a search() followed by a read() (if needed) using the
        provided search criteria

        :param request: a JSON-RPC request object
        :type request: openerpweb.JsonRequest
        :param str model: the name of the model to search on
        :param fields: a list of the fields to return in the result records
        :type fields: [str]
        :param int offset: from which index should the results start being returned
        :param int limit: the maximum number of records to return
        :param list domain: the search domain for the query
        :param dict context: the context in which the search should be executed
        :param list sort: sorting directives
        :returns: a list of result records
        :rtype: list
        """
        Model = request.session.model(model)
        ids = Model.search(domain or [], offset or 0, limit or False,
                           sort or False, context or False)
        if fields and fields == ['id']:
            # shortcut read if we only want the ids
            return map(lambda id: {'id': id}, ids)
        return Model.read(ids, fields or False)

    @openerpweb.jsonrequest
    def get(self, request, model, ids, fields=False):
        return self.do_get(request, model, ids, fields)
    def do_get(self, request, model, ids, fields=False):
        """ Fetches and returns the records of the model ``model`` whose ids
        are in ``ids``.

        The results are in the same order as the inputs, but elements may be
        missing (if there is no record left for the id)

        :param request: the JSON-RPC2 request object
        :type request: openerpweb.JsonRequest
        :param model: the model to read from
        :type model: str
        :param ids: a list of identifiers
        :type ids: list
        :returns: a list of records, in the same order as the list of ids
        :rtype: list
        """
        Model = request.session.model(model)
        records = Model.read(ids, fields)

        record_map = dict((record['id'], record) for record in records)

        return [record_map[id] for id in ids if record_map.get(id)]
    @openerpweb.jsonrequest

    def load(self, req, model, id, fields):
        m = req.session.model(model)
        value = {}
        r = m.read([id])
        if r:
            value = r[0]
        return {'value': value}

    @openerpweb.jsonrequest
    def save(self, req, model, id, data, context={}):
        m = req.session.model(model)
        r = m.write([id], data, context)
        return {'result': r}

    @openerpweb.jsonrequest
    def call(self, req, model, method, ids, args):
        m = req.session.model(model)
        r = getattr(m, method)(ids, *args)
        return {'result': r}

    @openerpweb.jsonrequest
    def default_get(self, req, model, fields, context={}):
        m = req.session.model(model)
        r = m.default_get(fields, context)
        return {'result': r}

class View(openerpweb.Controller):
    def fields_view_get(self, session, model, view_id, view_type, transform=True):
        Model = session.model(model)
        r = Model.fields_view_get(view_id, view_type)
        if transform:
            context = {} # TODO: dict(ctx_sesssion, **ctx_action)
            xml = self.transform_view(r['arch'], session, context)
        else:
            xml = ElementTree.fromstring(r['arch'])
        r['arch'] = Xml2Json.convert_element(xml)
        return r

    def normalize_attrs(self, elem, context):
        """ Normalize @attrs, @invisible, @required, @readonly and @states, so
        the client only has to deal with @attrs.

        See `the discoveries pad <http://pad.openerp.com/discoveries>`_ for
        the rationale.

        :param elem: the current view node (Python object)
        :type elem: xml.etree.ElementTree.Element
        :param dict context: evaluation context
        """
        # If @attrs is normalized in json by server, the eval should be replaced by simplejson.loads
        attrs = eval(elem.attrib.get('attrs', '{}'))
        if 'states' in elem.attrib:
            if 'invisible' not in attrs:
                attrs['invisible'] = []
                # This should be done by the server
            attrs['invisible'].append(('state', 'not in', elem.attrib['states'].split(',')))
            del(elem.attrib['states'])
        if attrs:
            elem.attrib['attrs'] = simplejson.dumps(attrs)
        for a in ['invisible', 'readonly', 'required']:
            if a in elem.attrib:
                # In the XML we trust
                avalue = bool(eval(elem.attrib.get(a, 'False'),
                                   {'context': context or {}}))
                if not avalue:
                    del elem.attrib[a]
                else:
                    elem.attrib[a] = '1'
                    if a == 'invisible' and 'attrs' in elem.attrib:
                        del elem.attrib['attrs']

    def transform_view(self, view_string, session, context=None):
        # transform nodes on the fly via iterparse, instead of
        # doing it statically on the parsing result
        parser = ElementTree.iterparse(StringIO(view_string), events=("start",))
        root = None
        for event, elem in parser:
            if event == "start":
                if root is None:
                    root = elem
                self.normalize_attrs(elem, context)
                self.parse_domains_and_contexts(elem, session)
        return root

    def parse_domain(self, elem, attr_name, session):
        """ Parses an attribute of the provided name as a domain, transforms it
        to either a literal domain or a :class:`openerpweb.nonliterals.Domain`

        :param elem: the node being parsed
        :type param: xml.etree.ElementTree.Element
        :param str attr_name: the name of the attribute which should be parsed
        :param session: Current OpenERP session
        :type session: openerpweb.openerpweb.OpenERPSession
        """
        domain = elem.get(attr_name, '').strip()
        if domain:
            try:
                elem.set(
                    attr_name,
                    openerpweb.ast.literal_eval(
                        domain))
            except ValueError:
                # not a literal
                elem.set(attr_name,
                         openerpweb.nonliterals.Domain(session, domain))

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
        self.parse_domain(elem, 'domain', session)
        self.parse_domain(elem, 'filter_domain', session)
        context_string = elem.get('context', '').strip()
        if context_string:
            try:
                elem.set('context',
                         openerpweb.ast.literal_eval(context_string))
            except ValueError:
                elem.set('context',
                         openerpweb.nonliterals.Context(
                             session, context_string))

class FormView(View):
    _cp_path = "/base/formview"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        fields_view = self.fields_view_get(req.session, model, view_id, 'form')
        return {'fields_view': fields_view}

class ListView(View):
    _cp_path = "/base/listview"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        fields_view = self.fields_view_get(req.session, model, view_id, 'tree')
        return {'fields_view': fields_view}

class SearchView(View):
    _cp_path = "/base/searchview"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        fields_view = self.fields_view_get(req.session, model, view_id, 'search')
        return {'fields_view': fields_view}

class SideBar(View):
    _cp_path = "/base/sidebar"

    @openerpweb.jsonrequest
    def get_actions(self, request, model, object_id=0):
        result = load_actions_from_ir_values(request, "action", "client_action_multi",
                                             [[model, object_id]], False, {})
        return result

class Action(openerpweb.Controller):
    _cp_path = "/base/action"

    @openerpweb.jsonrequest
    def load(self, req, action_id):
        return {}
