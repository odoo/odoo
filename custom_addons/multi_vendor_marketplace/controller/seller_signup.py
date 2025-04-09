# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import logging
import werkzeug
from werkzeug.urls import url_encode
from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.auth_signup.controllers.main import ensure_db, \
    LOGIN_SUCCESSFUL_PARAMS, SIGN_UP_REQUEST_PARAMS

_logger = logging.getLogger(__name__)

LOGIN_SUCCESSFUL_PARAMS.add('account_created')


class SellerSignup(AuthSignupHome):
    """Class for sellers signup"""

    @http.route(['/seller/list'], type="http", auth="public",
                website="True")
    def seller_list(self):
        """ Goto the Sellers List"""
        return http.Response(
            template='multi_vendor_marketplace.seller_list',
            qcontext={
                'seller': request.env['res.partner'].sudo().search(
                    [('state', '=', 'Approved'), ('is_published', '=', True)])
            })

    @http.route(['/seller/profile/<string:profile_url>'], type="http",
                auth="public", website="True")
    def seller_profile(self, **kwargs):
        """Goto The corresponding seller-shop Using Profile URl"""
        user_obj = request.env['res.partner'].sudo().search(
            [('profile_url_value', '=', kwargs.get('profile_url'))])
        recent_products = request.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.recent_products')
        review_count = request.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.seller_review_count')
        current_user = request.env.user.sudo()
        review = request.env['seller.review'].sudo().search(
            [('seller_id', '=', user_obj.id), ('state', '=', 'published')],
            limit=int(review_count))
        product = request.env['product.template'].sudo().search(
            [('seller_id', '=', user_obj.id), ('is_published', '=', True)])
        recently_add_product = request.env['product.template'].sudo().search(
            [('seller_id', '=', user_obj.id), ('is_published', '=', True)],
            limit=int(recent_products),
            order='seller_id desc')
        params = request.env['res.config.settings'].sudo().search(
            [], order='create_date DESC', limit=1)
        partner = request.env['res.partner'].sudo().browse(user_obj.id)
        avg_rating = partner.avg_rating
        total = request.env['seller.review'].sudo().search_count(
            [('seller_id', '=', partner.id)])
        if total != 0:
            five = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', partner.id), ('rating', '=', '5')])
            four = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', partner.id), ('rating', '=', '4')])
            three = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', partner.id), ('rating', '=', '3')])
            two = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', partner.id), ('rating', '=', '2')])
            one = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', partner.id), ('rating', '=', '1')])
            five = round(five / total * 100)
            four = round(four / total * 100)
            three = round(three / total * 100)
            two = round(two / total * 100)
            one = round(one / total * 100)
        else:
            five = four = three = two = one = 0
        values = {
            'res_users': user_obj,
            'product': product,
            'recently_add_product': recently_add_product,
            'config': params,
            'cr_user': current_user,
            'avg': round(avg_rating, 2),
            'prod_count': request.env['product.template'].sudo().search_count(
                [('seller_id', '=', user_obj.id),
                 ('is_published', '=', True)]),
            'sale_count': request.env['sale.order.line'].sudo().search_count(
                [('seller_id', '=', user_obj.id)]),
            'average': avg_rating,
            'five': str(five),
            'four': str(four),
            'three': str(three),
            'two': str(two),
            'one': str(one),
            'review': review
        }
        response = http.Response(
            template='multi_vendor_marketplace.seller_product',
            qcontext=values)
        return response.render()

    @http.route(['/sell'], type="http", auth="public", website="True")
    def home_page(self, **post):
        """Goto the sell menu and here we can see the seller registration
        button """
        params = request.env['res.config.settings'].sudo().search(
            [], order='create_date desc', limit=1)
        values = {
            'config': params}
        response = http.Response(
            template='multi_vendor_marketplace.sell_page',
            qcontext=values)
        return response.render()

    @http.route(['/seller_shop'], type="http", auth="public",
                website="True", csrf=False)
    def seller_shop(self, seller_id=None, product_id=None, **kwargs):
        """Goto the corresponding Seller shop"""
        if product_id:
            pr = request.env['product.product'].sudo().browse(int(product_id))
            user_obj = pr.seller_id
        else:
            pr = request.env['res.partner'].sudo().browse(int(seller_id))
            user_obj = pr
        recent_products = request.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.recent_products')
        review_count = request.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.seller_review_count')
        current_user = request.env.user.sudo()
        review = request.env['seller.review'].sudo().search(
            [('seller_id', '=', user_obj.id), ('state', '=', 'published')],
            limit=int(review_count))
        product = request.env['product.template'].sudo().search(
            [('seller_id', '=', user_obj.id), ('is_published', '=', True)])
        recently_add_product = request.env['product.template'].sudo().search(
            [('seller_id', '=', user_obj.id), ('is_published', '=', True)],
            limit=int(recent_products),
            order='seller_id desc')
        params = request.env['res.config.settings'].sudo().search(
            [], order='create_date DESC', limit=1)
        res_partner = request.env['res.partner'].sudo().browse(user_obj.id)
        avg_rating = res_partner.avg_rating
        total = request.env['seller.review'].sudo().search_count(
            [('seller_id', '=', res_partner.id)])
        if total != 0:
            five = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', res_partner.id), ('rating', '=', '5')])
            four = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', res_partner.id), ('rating', '=', '4')])
            three = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', res_partner.id), ('rating', '=', '3')])
            two = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', res_partner.id), ('rating', '=', '2')])
            one = request.env['seller.review'].sudo().search_count(
                [('seller_id', '=', res_partner.id), ('rating', '=', '1')])
            five = round(five / total * 100)
            four = round(four / total * 100)
            three = round(three / total * 100)
            two = round(two / total * 100)
            one = round(one / total * 100)
        else:
            five = four = three = two = one = 0
        values = {
            'res_users': user_obj,
            'product': product,
            'recently_add_product': recently_add_product,
            'config': params,
            'cr_user': current_user,
            'avg': round(avg_rating, 2),
            'prod_count': request.env['product.template'].sudo().search_count(
                [('seller_id', '=', user_obj.id),
                 ('is_published', '=', True)]),
            'sale_count': request.env['sale.order.line'].sudo().search_count(
                [('seller_id', '=', user_obj.id)]),
            'average': avg_rating,
            'five': str(five),
            'four': str(four),
            'three': str(three),
            'two': str(two),
            'one': str(one),
            'review': review
        }
        response = http.Response(
            template='multi_vendor_marketplace.seller_product',
            qcontext=values)
        return response.render()

    @http.route('/seller_reg', type='http', auth='public', website=True,
                sitemap=False, csrf=False)
    def seller_signup(self, *args, **kw):
        """Seller Registration Form"""
        qcontext = self.get_auth_signup_qcontext()
        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()
        if 'error' not in qcontext and request.httprequest.method == 'POST':
            if request.env["res.partner"].sudo().search(
                    [("profile_url_value", "=", kw.get("profile_url"))]):
                qcontext["error"] = _(
                    "Another user has already registered using this Profile "
                    "url.")
            else:
                try:
                    profile_url = {'profile_url': 1}
                    qcontext.update(profile_url)
                    self.do_signup(qcontext)
                    base_url = request.env[
                        'ir.config_parameter'].sudo().get_param(
                        'web.base.url')
                    request.env["res.partner"].sudo().search(
                        [('email', '=', kw.get('login'))]).write(
                        {'profile_url': base_url + "/seller/profile/" + kw.get(
                            'profile_url'),
                         'profile_url_value': kw.get('profile_url')})
                    if qcontext.get('token'):
                        user = self.env['res.users']
                        user_sudo = user.sudo().search(
                            user._get_login_domain(qcontext.get('login')),
                            order=user._get_login_order(), limit=1
                        )
                        template = request.env.ref(
                            'auth_signup.mail_template_user_input_invite',
                            raise_if_not_found=False)
                        if user_sudo and template:
                            template.sudo().send_mail(user_sudo.id,
                                                      force_send=True)
                    return self.web_login(*args, **kw)
                except UserError as e:
                    qcontext['error'] = e.args[0]
                except (SignupError, AssertionError) as e:
                    if request.env["res.users"].sudo().search(
                            [("login", "=", qcontext.get("login"))]):
                        qcontext["error"] = _(
                            "Another user is already registered using this "
                            "email address.")
                    else:
                        _logger.error("%s", e)
                        qcontext['error'] = _(
                            "Could not create a new account.")
        elif 'signup_email' in qcontext:
            user = request.env['res.users'].sudo().search(
                [('email', '=', qcontext.get('signup_email')),
                 ('state', '!=', 'new')], limit=1)
            if user:
                return request.redirect('/web/login?%s' % url_encode(
                    {'login': user.login, 'redirect': '/web'}))
        response = request.render('multi_vendor_marketplace.mark', qcontext)
        return response

    def _prepare_signup_values(self, qcontext):
        """Super The _prepare_signup_values function to pass values  not to
        Override The Default Sign Up"""
        values = {key: qcontext.get(key) for key in
                  ('login', 'name', 'password')}
        if not values:
            raise UserError(_("The form was not properly filled in."))
        if values.get('password') != qcontext.get('confirm_password'):
            raise UserError(
                _("Passwords do not match; please retype them."))
        supported_lang_codes = [code for code, _ in
                                request.env['res.lang'].get_installed()]
        lang = request.context.get('lang', '')
        if lang in supported_lang_codes:
            values['lang'] = lang
        values['profile_url'] = int(
            qcontext.get('profile_url')) if qcontext.get(
            'profile_url') else 0
        return values
