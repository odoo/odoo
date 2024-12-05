# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.tools import lazy


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)
        affiliate_id = request.httprequest.args.get('affiliate_id')
        if affiliate_id:
            request.session['affiliate_id'] = int(affiliate_id)

    @classmethod
    def _frontend_pre_dispatch(cls):
        super()._frontend_pre_dispatch()

        # lazy to make sure those are only evaluated when requested
        request.pricelist = lazy(request.website._get_and_cache_current_pricelist)

        # SUDOED records
        request.cart = lazy(request.website._get_and_cache_current_order)
        request.fiscal_position = lazy(request.website._get_and_cache_current_fiscal_position)
