# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

import base64
import logging
import json
from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class MailController(http.Controller):
    _cp_path = '/mail'

    @http.route(['/mail/confirm_domain'], type='json', auth="public", methods=['POST'], website=True)
    def confirm_domain(self, domain_name, contract_id,  **kw):
        """
        This controller is called when the customers submits the domain name from the controller.
        """
        contract = request.env['saas.contract'].sudo().search([('domain_name', '=ilike', domain_name), ('state', '!=', 'cancel')])
        if contract:
            _logger.info("---------ALREADY TAKEN--------%r", contract)
            return dict(
                status=1
            )
        else:
            _logger.info("---------CREATING CLIENT--------%r", contract)
            contract = request.env['saas.contract'].sudo().browse(int(contract_id))
            if contract.state == 'draft' and ((contract.server_id and contract.server_id.total_clients < contract.server_id.max_clients) or (not contract.server_id)) and not contract.saas_client:
                contract.domain_name = domain_name
                try:
                    # Creating Client -- Script Called--START
                    contract.create_saas_client()
                    # Creating Client -- Script Called--END
                    if contract.saas_client and contract.saas_client.client_url:
                        _logger.info("---Success----------")
                        return dict(
                            status=2,
                            url=contract.saas_client.client_url
                        )
                except Exception as e:
                    body = "An Exception is occur while creating client : {}".format(e)
                    contract.message_post(body=body, subject="Client Creation Exceptions")
                    _logger.info("---1----------%r", e)
                    return dict(
                        status=3,
                    )
            _logger.info("---3----------")
            body = "An Exception occur: \n Please Check Contract Not be in Draft State, or Maximum Client Limit Exceeds, or Client Exist with same Contract"
            contract.message_post(body=body, subject="Client Creation Exceptions")
            return dict(
                status=3,
            )

    @http.route('/mail/contract/subdomain', type='http', auth='public', website=True)
    def mail_action_view(self, contract_id=None, token=None, partner_id=None, **kwargs):
        """
        This controller returns the domain selection portal page for the customer.
        """
        if contract_id and token and partner_id:
            contract = request.env['saas.contract'].browse(int(contract_id))
            if contract.exists() and (contract.partner_id.id == int(partner_id)) and (contract.token == token) and (contract.state == 'draft'):
                return request.render('odoo_saas_kit.subdomain_page', {
                    'contract_id': contract_id,
                    'base_url': contract.saas_domain_url,
                    'page_name': 'saas_subdomain',
                })
            else:
                return request.redirect('/my')
        else:
            return request.redirect('/error')

    @http.route('/client/domain-created/redirect', type="http", auth="public", website=True)
    def domain_set_template(self):
        return request.render('odoo_saas_kit.redirect_page')


class CustomWebsiteSale(WebsiteSale):
    
    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        """
        Override the controller to add the extra line for user pricing in website with custom price based on number of users and number of cycles.
        """
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)
        product_custom_attribute_values = None
        if kw.get('product_custom_attribute_values'):
            product_custom_attribute_values = json.loads(kw.get('product_custom_attribute_values'))

        no_variant_attribute_values = None
        if kw.get('no_variant_attribute_values'):
            no_variant_attribute_values = json.loads(kw.get('no_variant_attribute_values'))

        plan_line = sale_order._cart_update(
            product_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values
        )
        product = request.env['product.product'].sudo().browse(int(product_id))
        if product.saas_plan_id and product.saas_plan_id.per_user_pricing and product.saas_plan_id.user_product:
            user_pricing_product = product.saas_plan_id.user_product
            number_of_user = kw.get('number_of_user')
            line_config = sale_order._cart_update(
                product_id=int(user_pricing_product.id),
                add_qty=add_qty,
            )
            product_amount = int(number_of_user) * int(product.user_cost)
            order_line = request.env['sale.order.line'].sudo().browse(int(line_config['line_id']))
            plan_line_id = request.env['sale.order.line'].sudo().browse(int(plan_line['line_id']))
            plan_line_id.write({
                'plan_line_id': order_line.id,
            })
            plan_line_id._cr.commit()
            order_line.write({'price_unit': product_amount,
            'is_user_product': True,
            'saas_users': int(number_of_user),
            'linked_line_id': plan_line_id.id,
            })        
            order_line._cr.commit()
        return request.redirect("/shop/cart")
