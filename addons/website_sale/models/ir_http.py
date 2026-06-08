# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.tools import lazy


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)
        affiliate_id = request.httprequest.args.get("affiliate_id")
        if affiliate_id:
            request.session["affiliate_id"] = int(affiliate_id)

    @classmethod
    def _frontend_pre_dispatch(cls):
        super()._frontend_pre_dispatch()

        # lazy to make sure those are only evaluated when requested
        # All those records are sudoed !
        website = request.env.website
        request.cart = lazy(website._get_and_cache_current_cart)
        request.fiscal_position = lazy(website._get_and_cache_current_fiscal_position)
        request.pricelist = lazy(website._get_and_cache_current_pricelist)

    @classmethod
    def _slug(cls, value: models.BaseModel | tuple[int, str]) -> str:
        if isinstance(value, models.BaseModel):
            return super()._slug(
                value.with_context(show_attribute=False, show_parent_categories=False)
            )
        return super()._slug(value)
