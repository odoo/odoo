# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from odoo.http import Controller, request, route
from odoo.tools import consteq


class ProductFeed(Controller):

    @route(
        '/gmc.xml',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def gmc_feed(self, feed_id='', access_token=''):
        """Serve a dynamic XML feed to synchronize the eCommerce products with Google Merchant
        Center (GMC).

        This method generates an XML feed containing information about eCommerce products.
        The feed is configured via the `product.feed` model, allowing customization such as:
        - Localization by specifying a language or pricelist (currency).
        - Filtering products by category or categories.

        Notes:
        - The feed is only accessible through a valid `access_token`.
        - A feed will contain at most 6000 products. If there are more than 6000 products,
          only the first 6000 will be included in the feed. This is a technical limit, but a soft
          limit of 5000 products is also enforced on the `product.feed` record.

        See also https://support.google.com/merchants/answer/7052112 for the XML format.

        :return: The XML feed compressed using GZIP.
        :rtype: bytes
        """
        if not request.website.enabled_gmc_src:
            raise NotFound()

        feed_sudo = self._find_and_check_feed_access(feed_id, access_token)

        if feed_sudo.website_id != request.website:
            raise BadRequest("Website does not match.")

        compressed_gmc_xml = feed_sudo._render_and_cache_compressed_gmc_feed()

        return request.make_response(compressed_gmc_xml, [
            ('Content-Type', 'application/xml; charset=utf-8'),
            ('Content-Encoding', 'gzip'),
        ])

    def _find_and_check_feed_access(self, feed_id, access_token):
        """Find the feed by its ID and validate its access token.

        :param str feed_id: The ID of the feed to validate.
        :param str access_token: The access token associated with the feed.
        :raises BadRequest: If the feed ID cannot be converted to an integer.
        :raises NotFound: If the feed ID does not match any existing feed.
        :raises Forbidden: If the provided access token does not match the feed's access token.
        :return: The feed record if access is successfully validated, in sudo mode.
        :rtype: product.feed
        """
        try:
            feed_id = int(feed_id)
        except ValueError:
            raise BadRequest()
        feed_sudo = request.env['product.feed'].sudo().browse(feed_id).exists()
        if not feed_sudo:
            raise NotFound()

        if not consteq(feed_sudo.access_token, access_token):
            raise Forbidden()

        return feed_sudo
