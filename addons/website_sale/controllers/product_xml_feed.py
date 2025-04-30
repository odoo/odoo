# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo.fields import Domain
from odoo.http import Controller, request, route
from odoo.tools.urls import urljoin as url_join


class ProductXmlFeed(Controller):

    @route(
        ['/gmc.xml', '/gmc-<pricelist_name_ilike>.xml'],
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def gmc_feed(self, pricelist_name_ilike=None):
        """
        Serve the Google Merchant Center product feed.
            - Supports optional pricelist via `/gmc-<pricelist-name>.xml`
            - Uses the GMC XML template and product formatting
            - Only serves if GMC feed is enabled on the website
        """
        if not (request.website.enabled_gmc_src and request.website.has_ecommerce_access()):
            raise NotFound()
        return self._render_feed(
            pricelist_name_ilike=pricelist_name_ilike,
            template='website_sale.gmc_xml',
            prepare_items_fn=lambda products: products._prepare_gmc_items(),
        )

    @route(
        ['/meta.xml', '/meta-<pricelist_name_ilike>.xml'],
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def meta_feed(self, pricelist_name_ilike=None):
        """
        Serve the Meta product catalog feed.
            - Supports optional pricelist via `/meta-<pricelist-name>.xml`
            - Uses the Meta XML template and product formatting
            - Only serves if Meta feed is enabled on the website
        """
        if not (request.website.enabled_meta_src and request.website.has_ecommerce_access()):
            raise NotFound()
        return self._render_feed(
            pricelist_name_ilike=pricelist_name_ilike,
            template='website_sale.meta_xml',
            prepare_items_fn=lambda products: products._prepare_meta_items(),
        )

    def _render_feed(self, pricelist_name_ilike, prepare_items_fn, template):
        """Generate data source/feed for the given enabled product feed.
        - The feed adapts to the context lang; product titles, descriptions, etc.
        - By default, it uses the connected user's pricelist. A specific pricelist can be selected
          by including its name or part in the URL. E.g., /gmc-christmas.xml or /meta-christ.xml
          will force the "christmas" pricelist as well as the pricelist's currency.
          Note: All the product link will also force the pricelist to ensure the feed's
          prices corresponds to the website's prices.
        """
        website = request.website

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

        # Generate data source for GMC/Meta.
        homepage_url = website.homepage_url or '/'
        website_homepage = website._get_website_pages(
            [('url', '=', homepage_url), ('website_id', '!=', False)], limit=1,
        )
        products = request.env['product.product'].search(Domain.AND([
            Domain('is_published', '=', True),
            Domain('type', 'in', ('consu', 'combo')),
            website.website_domain(),
        ]))
        feed_data = {
            'title': website_homepage.website_meta_title or website.name,
            'link': url_join(website.get_base_url(), request.env['ir.http']._url_lang(homepage_url)),
            'description': website_homepage.website_meta_description,
            'items': prepare_items_fn(products),
        }
        content = request.env['ir.ui.view'].sudo()._render_template(template, feed_data)
        return request.make_response(content, [('Content-Type', 'application/xml;charset=utf-8')])
