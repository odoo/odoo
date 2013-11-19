# -*- coding: utf-8 -*-
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
        self.regex = r'(?:[A-Za-z0-9-_]+?-)(\d+)$'

    def to_url(self, value):
        [(_, name)] = value.name_get()
        return "%s-%d" % (slugify(name), value.id)

    def generate(self):
        for id in request.registry[self.model].search(request.cr, request.uid, [], context=request.context):
            yield request.registry[self.model].browse(request.cr, request.uid, id, context=request.context)
