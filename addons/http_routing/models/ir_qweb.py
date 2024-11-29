# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)
BAD_REQUEST = """Missing request.is_frontend attribute.

The request.is_frontend attribute is missing, this means that although
http_routing is installed and that all incoming requests SHOULD be
going through ir.http._match (which sets that attribute),
there are some rogue requests which do not. This is likely due to a
@route(auth='none') controller which creates its own registry and attempts
to render a template (e.g. odoo/odoo#99667).

The following expectations MUST hold:

When:
* there is an incoming http request (request is truthy)
* there is a registry loaded (models are in use)
* http_routing is installed (dependency of both portal and website)

Then:
* request.is_frontend is set

Failure to meet this expectation can lead to downstream problems, e.g.
here inside of http_routing's ir.qweb. Solutions vary, the one used
inside of #99667 is to use the request.borrow_request context manager to
temporary hide the incoming http request.
"""


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _prepare_environment(self, values):
        irQweb = super()._prepare_environment(values)
        values['slug'] = self.env['ir.http']._slug
        values['unslug_url'] = self.env['ir.http']._unslug_url

        if not irQweb.env.context.get('minimal_qcontext') and request:
            if not hasattr(request, 'is_frontend'):
                _logger.warning(BAD_REQUEST, stack_info=True)
            elif request.is_frontend:
                return irQweb._prepare_frontend_environment(values)

        return irQweb

    def _prepare_frontend_environment(self, values):
        values['url_for'] = self.env['ir.http']._url_for
        values['url_localized'] = self.env['ir.http']._url_localized
        return self
