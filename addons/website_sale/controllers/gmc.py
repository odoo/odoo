# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo.fields import Domain
from odoo.http import Controller, request, route
from odoo.tools.urls import urljoin as url_join


class GoogleMerchantCenter(Controller):

    @route(
        ['/gmc.xml', '/gmc-<pricelist_name_ilike>.xml'],
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def gmc_data_source(self, pricelist_name_ilike=None):
        """Generate a Google Merchant Center (GMC) data source/feed.

        - The feed adapts to the context lang; product titles, descriptions, etc.
        - By default, it uses the connected user's pricelist. A specific pricelist can be selected
          by including its name or part in the URL. E.g., /gmc-christmas.xml or /gmc-christ.xml will
          force the "christmas" pricelist as well as the pricelist's currency.
          Note: All the product link will also force the pricelist to ensure the feed's
          prices corresponds to the website's prices.

        :param str pricelist_name_ilike: The name of the pricelist to use for the feed.
        :return: The rendered GMC data source in XML.
        :rtype: str
        """
        website = request.website
        if not website.enabled_gmc_src or not website.has_ecommerce_access():
            raise NotFound()

        # Find the pricelist by name if specified.
        if pricelist_name_ilike is not None:
            pricelist_sudo = request.env['product.pricelist'].sudo().search(
                Domain.AND([
                    Domain('name', 'ilike', pricelist_name_ilike),
                    request.env['product.pricelist']._get_website_pricelists_domain(website),
                ]),
                limit=1,
            )
            if not pricelist_sudo:
                raise NotFound()
            request.pricelist = pricelist_sudo

        # Generate the GMC data source.
        homepage_url = website.homepage_url or '/'
        website_homepage = website._get_website_pages(
            [('url', '=', homepage_url), ('website_id', '!=', False)], limit=1,
        )
        products = request.env['product.product']
        gmc_data = {
            'title': website_homepage.website_meta_title or website.name,
            'link': url_join(website.get_base_url(), request.env['ir.http']._url_lang(homepage_url)),
            'description': website_homepage.website_meta_description,
            'items': products._prepare_gmc_items(),
        }
        content = request.env['ir.ui.view'].sudo()._render_template(
            'website_sale.gmc_xml', gmc_data,
        )
        return request.make_response(content, [('Content-Type', 'application/xml;charset=utf-8')])
