# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac

from odoo import _, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request
from odoo.addons.sale_shopee import const, utils


class ShopeeController(http.Controller):

    @http.route(
        '/shopee/return_from_authorization/<int:account_id>/<int:company_id>/<int:timestamp>/<string:sign>',
        type='http',
        methods=['GET'],
        auth='user',
    )
    def shopee_return_from_authorization(
        self, account_id, company_id, timestamp, sign, code=False, shop_id=False, main_account_id=False
    ):
        """ Callback from Shopee after the user has authorized the app.

        The authorization code is stored in the database and used to retrieve the access token.

        :param int account_id: The Shopee account for which the authorization code is being stored.
        :param int company_id: The company ID from which the flow was initiated.
        :param int timestamp: The timestamp of the request.
        :param str sign: The signature of the request.
        :param str code: The authorization code provided by Shopee.
        :param str shop_id: The shop identifier provided by Shopee.
        :param str main_account_id: The main account identifier provided by Shopee.
        :rtype: http.response
        """
        if not request.env.user.has_group('sales_team.group_sale_manager'):
            raise AccessError(_("You are not allowed to access this page."))

        path = const.API_OPERATIONS_MAPPING['auth_partner']['url_path']
        account = request.env['shopee.account'].browse(account_id)
        if not account:
            raise ValidationError(_(
                "Could not find Shopee account with id %(account)s", account=account_id
            ))

        if not hmac.compare_digest(sign, utils.get_public_sign(account, path, timestamp)):
            raise AccessError(_("The request signature is not valid."))

        shop_identifiers = [shop_id]
        shop_vals = {}
        if main_account_id:  # We can create all the shops linked to that account
            # A temporary shop is created to retrieve the shop_identifiers returned from
            # request_access_token. The temporary shop is then deleted after the shop_identifiers
            # are retrieved. This allows a cleaner code.
            temp_shop = request.env['shopee.shop'].create({
                'name': 'temporary shop',
                'shop_identifier': 1,
                'account_id': account_id,
            })
            shop_identifiers = utils.request_access_token(
                temp_shop.with_context(authorization_code=code), main_account_id=main_account_id
            )
            shop_vals.update({
                'access_token': temp_shop.access_token,
                'refresh_token': temp_shop.refresh_token,
                'access_token_expiration_date': temp_shop.access_token_expiration_date,
            })
            temp_shop.unlink()

        shop = request.env['shopee.shop']
        for identifier in shop_identifiers:
            shop = shop.with_context(
                authorization_code=code
            ).create_or_update_shop(company_id, account.id, identifier, shop_vals)

        # Craft the URL of the Shopee Shop form view
        redirect_url = f'/odoo/action-sale_shopee.action_shopee_account_list/{account.id}'
        if shop_id and shop:
            redirect_url = f'{redirect_url}/action-sale_shopee.action_shopee_shop_list/{shop.id}'

        return request.redirect(redirect_url, local=False)
