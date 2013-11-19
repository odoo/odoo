# -*- coding: utf-8 -*-
import werkzeug.routing
import openerp
from openerp.osv import orm
from openerp.http import request
from openerp.addons.base import ir

from ..utils import slugify

class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    def _get_converters(self):
        return dict(
            super(ir_http, self)._get_converters(),
            model=ModelConverter,
            page=PageConverter,
        )

    def _auth_method_public(self):
        if not request.session.uid:
            request.uid = request.registry['website'].get_public_user(
                request.cr, openerp.SUPERUSER_ID, request.context).id
        else:
            request.uid = request.session.uid


class ModelConverter(ir.ir_http.ModelConverter):
    def __init__(self, url_map, model=False):
        super(ModelConverter, self).__init__(url_map, model)
        self.regex = r'(?:[A-Za-z0-9-_]+?-)?(\d+)(?=$|/)'

    def to_url(self, value):
        if isinstance(value, orm.browse_record):
            [(id, name)] = value.name_get()
        else:
            # assume name_search result tuple
            id, name = value
        return "%s-%d" % (slugify(name), id)

    def generate(self, query=None):
        return request.registry[self.model].name_search(
            request.cr, request.uid,
            name=query or '',
            context=request.context)

class PageConverter(werkzeug.routing.PathConverter):
    """ Only point of this converter is to bundle pages enumeration logic

    Sads got: no way to get the view's human-readable name even if one exists
    """
    def generate(self, query=None):
        View = request.registry['ir.ui.view']
        views = View.search_read(
            request.cr, request.uid, [['page', '=', True]],
            fields=[], order='name', context=request.context)
        xids = View.get_external_id(
            request.cr, request.uid, [view['id'] for view in views],
            context=request.context)

        for view in views:
            xid = xids[view['id']]
            if xid and (not query or query in xid):
                yield xid
