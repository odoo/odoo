# -*- coding: utf-8 -*-
import glob, os
import pprint
from xml.etree import ElementTree
from cStringIO import StringIO

import simplejson

import openerpweb
import openerpweb.ast
import openerpweb.nonliterals

import cherrypy

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
# OpenERP Web mobile Controllers
#----------------------------------------------------------

class MOBILE(openerpweb.Controller):
    _cp_path = "/web_mobile/mobile"

    @openerpweb.jsonrequest
    def sc_list(self, req):
        return req.session.model('ir.ui.view_sc').get_sc(req.session._uid, "ir.ui.menu", {})

    @openerpweb.jsonrequest
    def logout(self,req):
        req.session_id = False
        req.session._uid = False


class DataSet(openerpweb.Controller):
    _cp_path = "/web_mobile/dataset"

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
        :param list sort: sorting directives
        :returns: a list of result records
        :rtype: list
        """
        Model = request.session.model(model)
        ids = Model.search(domain or [], offset or 0, limit or False,
                           sort or False, request.context)
        if fields and fields == ['id']:
            # shortcut read if we only want the ids
            return map(lambda id: {'id': id}, ids)
        return Model.read(ids, fields or False, request.context)

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
        :param fields: a list of fields to fetch, ``False`` or empty to fetch
                       all fields in the model
        :type fields: list | False
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
    def create(self, req, model, data, context={}):
        m = req.session.model(model)
        r = m.create(data, context)
        return {'result': r}

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
    def exec_workflow(self, req, model, id, signal):
        r = req.session.exec_workflow(model, id, signal)
        return {'result': r}

    @openerpweb.jsonrequest
    def default_get(self, req, model, fields, context={}):
        m = req.session.model(model)
        r = m.default_get(fields, context)
        return {'result': r}

class View(openerpweb.Controller):
    def fields_view_get(self, request, model, view_id, view_type,
                        transform=True, toolbar=False, submenu=False):
        Model = request.session.model(model)
        fvg = Model.fields_view_get(view_id, view_type, request.context,
                                    toolbar, submenu)
        if transform:
            evaluation_context = request.session.evaluation_context(
                request.context or {})
            xml = self.transform_view(
                fvg['arch'], request.session, evaluation_context)
        else:
            xml = ElementTree.fromstring(fvg['arch'])
        fvg['arch'] = Xml2Json.convert_element(xml)
        return fvg

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
        attrs = openerpweb.ast.literal_eval(elem.get('attrs', '{}'))
        if 'states' in elem.attrib:
            attrs.setdefault('invisible', [])\
                .append(('state', 'not in', elem.attrib.pop('states').split(',')))
        if attrs:
            elem.set('attrs', simplejson.dumps(attrs))
        for a in ['invisible', 'readonly', 'required']:
            if a in elem.attrib:
                # In the XML we trust
                avalue = bool(eval(elem.get(a, 'False'),
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

class ListView(View):
    _cp_path = "/web_mobile/listview"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id, toolbar=False):
        fields_view = self.fields_view_get(req, model, view_id, 'tree', toolbar=toolbar)
        return {'fields_view': fields_view}

    def fields_view_get(self, request, model, view_id, view_type="tree",
                        transform=True, toolbar=False, submenu=False):
        """ Sets @editable on the view's arch if it isn't already set and
        ``set_editable`` is present in the request context
        """
        view = super(ListView, self).fields_view_get(
            request, model, view_id, view_type, transform, toolbar, submenu)

        view_attributes = view['arch']['attrs']
        if request.context.get('set_editable')\
                and 'editable' not in view_attributes:
            view_attributes['editable'] = 'bottom'
        return view

    @openerpweb.jsonrequest
    def fill(self, request, model, id, domain,
             offset=0, limit=False):
        return self.do_fill(request, model, id, domain, offset, limit)

    def do_fill(self, request, model, id, domain,
                offset=0, limit=False):
        """ Returns all information needed to fill a table:

        * view with processed ``editable`` flag
        * fields (columns) with processed ``invisible`` flag
        * rows with processed ``attrs`` and ``colors``

        .. note:: context is passed through ``request`` parameter

        :param request: OpenERP request
        :type request: openerpweb.openerpweb.JsonRequest
        :type str model: OpenERP model for this list view
        :type int id: view_id, or False if none provided
        :param list domain: the search domain to search for
        :param int offset: search offset, for pagination
        :param int limit: search limit, for pagination
        :returns: hell if I have any idea yet
        """
        view = self.fields_view_get(request, model, id, toolbar=True)

        rows = DataSet().do_search_read(request, model,
                                        offset=offset, limit=limit,
                                        domain=domain)
        eval_context = request.session.evaluation_context(
            request.context)
        return {
            'view': view,
            'records': [
                {'data': dict((key, {'value': value})
                              for key, value in row.iteritems()),
                 'color': self.process_colors(view, row, eval_context)}
                for row in rows
            ]
        }

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
