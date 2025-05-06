# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request


class MainController(http.Controller):
    @http.route(['/seller_reg'], type='http', auth="public", website=True)
    def seller_registration(self, **post):
        """Страница регистрации продавца"""
        return request.render('cistech.seller_registration', {})
    
    @http.route(['/seller_reg/submit'], type='http', auth="public", website=True, methods=['POST'], csrf=True)
    def seller_registration_submit(self, **post):
        """Обработка формы регистрации продавца"""
        if not post.get('terms'):
            return request.redirect('/seller_reg?error=terms')
        
        # Создание записи о новом продавце
        vals = {
            'name': post.get('business_name'),
            'description': post.get('description'),
            'email': post.get('business_email'),
            'phone': post.get('business_phone'),
            'category': post.get('category'),
            'user_id': request.env.user.id if request.env.user.id != request.website.user_id.id else False,
        }
        
        # TODO: Здесь должна быть логика создания записи продавца
        
        # Перенаправление на страницу подтверждения
        return request.render('cistech.seller_registration_success', {
            'seller_name': post.get('business_name')
        }) 