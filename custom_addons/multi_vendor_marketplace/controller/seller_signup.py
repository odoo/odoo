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

    @http.route('/', type='http', auth='public', website=True)
    def homepage_redirect(self, **kwargs):
        return request.redirect('/shop')
    
    @http.route(['/profile'], type="http", auth="user", website=True)
    def user_profile(self, **kwargs):
        """Render the custom user profile page"""
        user = request.env.user
        return request.render('multi_vendor_marketplace.custom_user_profile', {
            'user': user,
        })
    
    @http.route('/profile/edit', type='http', auth='user', website=True)
    def edit_user_profile(self, **kwargs):
        """Render the Edit User Profile page"""
        user = request.env.user
        return request.render('multi_vendor_marketplace.edit_user_profile', {
            'user': user,
        })
    
    @http.route('/profile/save', type='http', auth='user', methods=['POST'], csrf=True)
    def save_profile(self, **post):
        """Save the updated user profile"""
        user = request.env.user
        user.sudo().write({
            'name': post.get('name'),
            'email': post.get('email'),
            'phone': post.get('phone'),
        })
        return request.redirect('/profile')

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
        
        # Список разрешенных стран по кодам с правильными русскими названиями
        country_mapping = [
            ('KG', 'Кыргызстан'),  # Первым в списке
            ('AZ', 'Азербайджан'),
            ('AM', 'Армения'),
            ('BY', 'Беларусь'),
            ('KZ', 'Казахстан'),
            ('MD', 'Молдова'),
            ('RU', 'Россия'),
            ('TJ', 'Таджикистан'),
            ('UZ', 'Узбекистан'),
            ('CN', 'Китай')
        ]
        
        # Получаем страны по кодам в нужном порядке
        countries = []
        for code, name in country_mapping:
            country = request.env['res.country'].sudo().search([('code', '=', code)], limit=1)
            if country:
                # Создаем временную копию страны с нужным русским именем
                custom_country = country.copy_data()[0]
                custom_country['id'] = country.id
                custom_country['name'] = name
                countries.append(type('obj', (object,), custom_country))
        
        qcontext.update({'countries': countries})
        
        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()
            
        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                # Получаем телефон и очищаем его для использования как логин
                phone = kw.get('phone', '').strip()
                if not phone:
                    qcontext['error'] = _("Phone number is required.")
                    return request.render('multi_vendor_marketplace.simplified_seller_registration', qcontext)
                
                # Используем телефон в качестве логина
                login = phone.replace(' ', '').replace('+', '').replace('-', '')
                
                # Проверяем пароль и подтверждение пароля
                password = kw.get('password', '')
                confirm_password = kw.get('confirm_password', '')
                
                if not password:
                    qcontext['error'] = _("Password is required.")
                    return request.render('multi_vendor_marketplace.simplified_seller_registration', qcontext)
                
                if password != confirm_password:
                    qcontext['error'] = _("Passwords do not match.")
                    return request.render('multi_vendor_marketplace.simplified_seller_registration', qcontext)
                
                # Генерируем URL профиля на основе имени и телефона
                name_part = kw.get('name', '').lower().split()[0] if kw.get('name') else ''
                if not name_part:
                    name_part = 'seller'
                phone_part = login[-4:] if len(login) >= 4 else login
                profile_url = f"{name_part}_{phone_part}"
                
                # Обновляем контекст для регистрации
                qcontext.update({
                    'login': login,
                    'name': kw.get('name'),
                    'password': password,
                    'confirm_password': confirm_password,
                    'profile_url': 1,
                    'profile_url_value': profile_url
                })
                
                # Обновляем kw для любых методов, которые могут его использовать
                kw['login'] = login
                kw['profile_url'] = profile_url
                
                # Получаем страну
                country_id = kw.get('country_id')
                
                # Регистрируем пользователя
                self.do_signup(qcontext)
                
                # Обновляем партнера с доп. информацией
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                partner = request.env["res.partner"].sudo().search([('email', '=', login)])
                if partner:
                    partner.write({
                        'phone': phone,
                        'profile_url': f"{base_url}/seller/profile/{profile_url}",
                        'profile_url_value': profile_url,
                        'country_id': int(country_id) if country_id else False
                    })
                
                # Перенаправляем на страницу входа с предварительно заполненным логином
                return werkzeug.utils.redirect(f'/web/login?login={login}')
                
            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                _logger.error("%s", e)
                qcontext['error'] = _("Could not create a new account.")
                
        return request.render('multi_vendor_marketplace.simplified_seller_registration', qcontext)

    @http.route('/', type='http', auth='public', website=True)
    def redirect_to_seller_shop(self, **kwargs):
        """Redirect homepage to default seller shop."""
        # Здесь можно указать конкретного продавца, или редиректить на список
        default_seller = request.env['res.partner'].sudo().search(
            [('state', '=', 'Approved'), ('is_published', '=', True)],
            limit=1
        )
        if default_seller:
            return request.redirect(f'/seller_shop?seller_id={default_seller.id}')
        else:
            return request.redirect('/seller/list')  # если нет продавцов, показываем список


    def _prepare_signup_values(self, qcontext):
        """Modified to handle simplified signup form values"""
        values = {
            'login': qcontext.get('login', ''),  # Ensure it's at least an empty string
            'name': qcontext.get('name', ''),
            'password': qcontext.get('password', '')
        }
        
        if not values.get('name'):
            raise UserError(_("Full name is required."))
            
        if not values.get('login'):
            raise UserError(_("Login is required."))
            
        if not values.get('password'):
            raise UserError(_("Password is required."))
            
        if values.get('password') != qcontext.get('confirm_password'):
            raise UserError(_("Passwords do not match; please retype them."))
            
        supported_lang_codes = [code for code, _ in request.env['res.lang'].get_installed()]
        lang = request.context.get('lang', '')
        if lang in supported_lang_codes:
            values['lang'] = lang
            
        values['profile_url'] = int(qcontext.get('profile_url')) if qcontext.get('profile_url') else 0
        return values



