# -*- coding: ascii -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import fnmatch
import werkzeug

from odoo import models
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug, unslug_url, url_for


def keep_query(*keep_params, **additional_params):
    """
    Generate a query string keeping the current request querystring's parameters specified
    in ``keep_params`` and also adds the parameters specified in ``additional_params``.

    Multiple values query string params will be merged into a single one with comma seperated
    values.

    The ``keep_params`` arguments can use wildcards too, eg:

        keep_query('search', 'shop_*', page=4)
    """
    if not keep_params and not additional_params:
        keep_params = ('*',)
    params = additional_params.copy()
    qs_keys = list(request.httprequest.args) if request else []
    for keep_param in keep_params:
        for param in fnmatch.filter(qs_keys, keep_param):
            if param not in additional_params and param in qs_keys:
                params[param] = request.httprequest.args.getlist(param)
    return werkzeug.urls.url_encode(params)


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _prepare_environment(self, values):
        irQweb = super()._prepare_environment(values)
        values['slug'] = slug
        values['unslug_url'] = unslug_url
        values['keep_query'] = keep_query

        if (not irQweb.env.context.get('minimal_qcontext') and
                request and request.is_frontend):
            return irQweb._prepare_frontend_environment(values)

        return irQweb

    def _prepare_frontend_environment(self, values):
        values['url_for'] = url_for
        return self
