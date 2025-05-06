# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request


class ProfileController(http.Controller):
    @http.route(['/profile', '/my/home'], type="http", auth="user", website=True)
    def user_profile(self, **kwargs):
        """Render the custom user profile page"""
        user = request.env.user
        
        # Для отладки добавим вывод в консоль
        print(f"RENDERING PROFILE FOR USER: {user.name}")
        
        # Make sure we pass the user object properly
        return request.render('cistech.custom_user_profile', {
            'user': user,
        })
    
    @http.route('/profile/edit', type='http', auth='user', website=True)
    def edit_user_profile(self, **kwargs):
        """Render the Edit User Profile page"""
        user = request.env.user
        return request.render('cistech.edit_user_profile', {
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
        
        # Обновление пароля если указано
        if post.get('new_password') and post.get('new_password') == post.get('confirm_password'):
            user.sudo().write({'password': post.get('new_password')})
            
        return request.redirect('/profile')
    
    @http.route(['/user/orders/status'], type='http', auth="user", website=True)
    def order_status(self, **kw):
        """Отображает статус заказов пользователя"""
        # Заглушка для демонстрации
        dummy_orders = [
            {
                'name': 'iPhone 15 Pro',
                'quantity': 1,
                'status': 'На доставке',
                'image_url': '/web/static/img/placeholder.png',
            },
            {
                'name': 'Smart Watch H20',
                'quantity': 2,
                'status': 'Обрабатывается',
                'image_url': '/web/static/img/placeholder.png',
            }
        ]
        return request.render('cistech.user_order_status', {
            'orders': dummy_orders
        })

    @http.route(['/user/orders/history'], type='http', auth="user", website=True)
    def order_history(self, **kw):
        """Отображает историю заказов пользователя"""
        # Заглушка для демонстрации
        import datetime
        today = datetime.datetime.now()
        dummy_orders = [
            {
                'name': 'Беспроводные наушники P30',
                'quantity': 1,
                'status': 'Доставлен',
                'image_url': '/web/static/img/placeholder.png',
                'date_order': today.strftime('%d.%m.%Y'),
                'time_order': today.strftime('%H:%M'),
            }
        ]
        return request.render('cistech.user_order_history', {
            'orders': dummy_orders
        })

    @http.route(['/user/orders/returns'], type='http', auth="user", website=True)
    def order_returns(self, **kw):
        """Отображает возвраты заказов пользователя"""
        # Заглушка для демонстрации
        import datetime
        today = datetime.datetime.now()
        dummy_returns = [
            {
                'name': 'Смартфон Samsung Galaxy S24',
                'quantity': 1,
                'status': 'Возврат принят',
                'image_url': '/web/static/img/placeholder.png',
                'date_return': today.strftime('%d.%m.%Y'),
                'time_return': today.strftime('%H:%M'),
            }
        ]
        return request.render('cistech.user_order_returns', {
            'returns': dummy_returns
        }) 