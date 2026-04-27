# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import time
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.sale_shopee import const, utils


class ShopeeAccount(models.Model):
    _name = 'shopee.account'
    _description = "Shopee Account"

    name = fields.Char(
        string="Name", help="The user-defined name of the account.", readonly=False, required=True
    )
    api_endpoint = fields.Selection(
        string="API Endpoint",
        help="The API endpoint to use for the Shopee API calls. There are production and testing"
             " endpoints. Among the endpoints, choose the one that is geographically closest to"
             " the marketplace you are targeting.",
        selection=[
            ('production_singapore', "Shopee Production Endpoint (Singapore)"),
            ('production_china', "Shopee Production Endpoint (China)"),
            ('production_brazil', "Shopee Production Endpoint (Brazil)"),
            ('test', "Shopee Testing Endpoint"),
            ('test_china', "Shopee Testing Endpoint (China)"),
        ],
        required=True,
    )
    company_ids = fields.Many2many(
        string="Allowed Company",
        help="If this field is empty, all companies will be allowed.",
        comodel_name='res.company',
    )
    partner_identifier = fields.Integer(string="Partner ID", required=True)
    partner_key = fields.Char(string="Partner Key", required=True)
    shop_ids = fields.One2many(
        string="Shops", comodel_name='shopee.shop', inverse_name='account_id'
    )
    shop_count = fields.Integer(string="Shop Count", compute='_compute_shop_count')

    # === COMPUTE METHODS === #

    @api.depends('shop_ids')
    def _compute_shop_count(self):
        for account in self:
            account.shop_count = len(account.shop_ids)

    # === ONCHANGE METHODS === #

    @api.onchange('api_endpoint')
    def _onchange_api_endpoint(self):
        if self.shop_ids:
            return {
                'warning': {
                    'title': _("Warning"),
                    'message': _("Changing API endpoint will reset the authorization of the shops."),
                }
            }

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to set the default name for the account. """
        for vals in vals_list:
            if not vals.get('name') and vals.get('partner_identifier'):
                vals['name'] = _(
                    "Shopee API Account - %(partner_id)s", partner_id=vals['partner_identifier']
                )

        return super().create(vals_list)

    def write(self, vals):
        """ Reset authorization of the shops if the API endpoint is changed. """
        if 'api_endpoint' in vals:
            if vals['api_endpoint'] != self.api_endpoint:
                self.shop_ids._reset_tokens()
        return super().write(vals)

    # === ACTION METHODS === #

    def action_view_shops(self):
        """ Open the shops related to the account in a list view. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Shops"),
            'res_model': 'shopee.shop',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.shop_ids.ids)],
        }

    def action_open_auth_link(self):
        """ Redirect the user to Shopee in order to authorize the app within Shopee. """
        self.ensure_one()

        path = const.API_OPERATIONS_MAPPING['auth_partner']['url_path']
        timestamp = int(time.time())
        sign = utils.get_public_sign(self, path, timestamp)
        company_id = self.env.company.id
        redirect_url = self.get_base_url() + \
                       f'/shopee/return_from_authorization/{self.id}/{company_id}/{timestamp}/{sign}'
        params = {
            'partner_id': self.partner_identifier,
            'timestamp': timestamp,
            'sign': sign,
            'redirect': redirect_url,
        }
        # The url needs to be accessed in order to give the authorization to the Shopee app.
        # It will call a callback with the authorization code needed to get the access and
        # refresh tokens. Check the status of the url before redirecting the user.
        url = f'{const.API_PATHS[self.api_endpoint]}{path}?{urls.url_encode(params)}'
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            content = response.json()
            if content.get('error'):
                raise UserError(_(
                    "Failed to authorize shop due to the following error:\n- %(message)s\n\n"
                    "One of the following input could be incorrect: Partner ID, Partner Key, or"
                    " API Endpoint.",
                    message=content.get('message'),
                ))

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }
