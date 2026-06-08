from odoo import http


class WebsiteSaleDonation(http.Controller):
    @http.route("/shop/donation/info", type="jsonrpc", auth="public", website=True, readonly=True)
    def donation_info(self):
        """Return the donation values needed by the donation snippet.

        :return: A dict with the values required by the donation snippet.
        :rtype: dict
        """
        donation_product = self.env.ref("website_sale.product_donation", raise_if_not_found=False)
        if not donation_product:
            return {}
        # Unpublished, sudo to allow public users to read it
        donation_product_sudo = donation_product.sudo()
        return {
            "product_template_id": donation_product_sudo.id,
            "product_id": donation_product_sudo.product_variant_id.id,
            **self._get_extra_donation_info(),
        }

    def _get_extra_donation_info(self):
        """Return additional values for the donation snippet.

        :return: A dict with extra values for the donation snippet.
        :rtype: dict
        """
        return {}
