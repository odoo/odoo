from odoo import http
from odoo.http import request

class CinetpayController(http.Controller):

    @http.route('/shop/buy_now/<int:order_id>', type='http', auth='public', website=True)
    def buy_now_form(self, order_id, **kwargs):
        # Récupérer le montant total transmis en paramètre
        amount_total = kwargs.get('amount_total')

        # Récupérer la commande associée
        order = request.env['sale.order'].sudo().browse(order_id)

        # Vérifier que la commande existe
        if not order.exists():
            return request.render('website.404')

        # Renvoyer le formulaire en passant l'objet order et amount_total
        return request.render('payment_cinetpay.buy_now_form', {
            'order': order,
            'amount_total': amount_total,
        })
