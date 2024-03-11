# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import warnings

from odoo import http
from odoo.api import call_kw
from odoo.http import request
from odoo.models import check_method_name
from .utils import clean_action


_logger = logging.getLogger(__name__)


class DataSet(http.Controller):

    @http.route('/web/dataset/search_read', type='json', auth="user")
    def search_read(self, model, fields=False, offset=0, limit=False, domain=None, sort=None):
        return request.env[model].web_search_read(domain, fields, offset=offset, limit=limit, order=sort)

    @http.route('/web/dataset/load', type='json', auth="user")
    def load(self, model, id, fields):
        warnings.warn("the route /web/dataset/load is deprecated and will be removed in Odoo 17. Use /web/dataset/call_kw with method 'read' and a list containing the id as args instead", DeprecationWarning)
        value = {}
        r = request.env[model].browse([id]).read()
        if r:
            value = r[0]
        return {'value': value}

    def _call_kw(self, model, method, args, kwargs):
        check_method_name(method)
        return call_kw(request.env[model], method, args, kwargs)

    @http.route('/web/dataset/call', type='json', auth="user")
    def call(self, model, method, args, domain_id=None, context_id=None):
        warnings.warn("the route /web/dataset/call is deprecated and will be removed in Odoo 17. Use /web/dataset/call_kw with empty kwargs instead", DeprecationWarning)
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
