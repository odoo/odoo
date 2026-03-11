# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.http import request
from odoo.addons.website_sale.models.website import (
    CART_SESSION_CACHE_KEY,
    FISCAL_POSITION_SESSION_CACHE_KEY,
    PRICELIST_SESSION_CACHE_KEY,
)




class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, args):
        if CART_SESSION_CACHE_KEY in request.session:
            request.update_context(sale_order_id=request.session[CART_SESSION_CACHE_KEY])
        if PRICELIST_SESSION_CACHE_KEY in request.session:
            request.update_context(pricelist_id=request.session[PRICELIST_SESSION_CACHE_KEY])
        if FISCAL_POSITION_SESSION_CACHE_KEY in request.session:
            request.update_context(fiscal_position_id=request.session[FISCAL_POSITION_SESSION_CACHE_KEY])
        super()._pre_dispatch(rule, args)

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        session_info.update({
            'add_to_cart_action': request.website.add_to_cart_action,
        })
        return session_info
