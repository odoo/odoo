# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug, unslug_url, url_for


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _prepare_environment(self, values):
        irQweb = super()._prepare_environment(values)
        values['slug'] = slug
        values['unslug_url'] = unslug_url

        if (not irQweb.env.context.get('minimal_qcontext') and
                request and request.is_frontend):
            return irQweb._prepare_frontend_environment(values)

        return irQweb

    def _prepare_frontend_environment(self, values):
        values['url_for'] = url_for
        return self
