# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.tools import file_open


class ApplePayController(http.Controller):
    _domain_association_url = "/.well-known/apple-developer-merchantid-domain-association"

    @http.route(_domain_association_url, type="http", auth="public", csrf=False)
    def apple_pay_get_domain_association_file(self):
        """Get the domain association file for Apple Pay.

        Payment providers handle the process of "merchant validation" described in Apple's
        documentation for Apple Pay on the Web. The provider and Apple will access this route to
        check the content of the file and verify that the web domain is registered.

        The file of the first enabled provider accepting Apple Pay is returned, as only one file can
        be served per web domain.

        See https://developer.apple.com/documentation/applepayontheweb/setting-up-your-server.

        :return: The content of the domain association file.
        :rtype: str
        :raise NotFound: If no enabled provider accepts Apple Pay.
        """
        provider_sudo = request.env["payment.provider"].sudo()._get_apple_pay_provider()
        if not provider_sudo:
            raise NotFound
        with file_open(provider_sudo._get_apple_pay_domain_association_file_path()) as f:
            return f.read()
