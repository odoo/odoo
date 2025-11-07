# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools
from odoo.fields import Domain
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

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        session_info.update({
            'add_to_cart_action': request.website.add_to_cart_action,
        })
        return session_info

    @classmethod
    def _frontend_pre_dispatch(cls):
        super()._frontend_pre_dispatch()

        # lazy to make sure those are only evaluated when requested
        # All those records are sudoed !
        request.cart = lazy(request.website._get_and_cache_current_cart)
        request.fiscal_position = lazy(request.website._get_and_cache_current_fiscal_position)
        request.pricelist = lazy(request.website._get_and_cache_current_pricelist)

    @api.model
    @tools.ormcache('path', 'website_id', cache='routing.rewrites')
    def url_unrewrite(self, path, website_id):
        """Return the opposite of `url_rewrite`. Note that this method does not support query
        params inside the path."""
        return self.env['website.rewrite'].sudo().search_fetch(
            Domain([
                ('redirect_type', '=', '308'),
                ('url_to', '=', path),
                ('website_id', 'in', (False, website_id)),
            ]),
            field_names=('url_from',),
            limit=1,
        ).url_from or path
