# Copyright 2015, 2017 Jairo Llopis <jairo.llopis@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale as Base


class WebsiteSale(Base):
    @route()
    def address(self, **kw):
        result = super(WebsiteSale, self).address(**kw)
        result.qcontext["country"] = result.qcontext.get("country") or request.website.company_id.country_id
        return result
