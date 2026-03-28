# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, modules
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, args):
        # Allow public user to use `fw` query string in test mode to ease tests
        force_website_id = request.httprequest.args.get('fw')
        if modules.module.current_test and force_website_id:
            request.env['website']._force_website(force_website_id)

        super()._pre_dispatch(rule, args)
