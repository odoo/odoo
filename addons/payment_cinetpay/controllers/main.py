from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class PaymentHistoryController(http.Controller):

    # 🧾 Route pour afficher l'historique des paiements
    @http.route('/payment/history', type='http', auth='user', website=True)
    def payment_history(self, **kwargs):
        # On récupère les 50 dernières commandes de l'utilisateur connecté
        sale_orders = request.env['sale.order'].sudo().search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ], order='date_order desc', limit=50)

        # On rend le template XML défini dans ton module
        return request.render('payment_cinetpay.payment_history_template', {
            'sale_orders': sale_orders
        })

    # 🔄 Route pour relancer un paiement annulé ou refusé
    @http.route('/payment/retry/<int:order_id>', type='http', auth='user', website=True)
    def retry_payment(self, order_id, **kwargs):
        order = request.env['sale.order'].sudo().browse(order_id)

        # On vérifie que la commande appartient bien à l'utilisateur
        if order.exists() and order.partner_id.id == request.env.user.partner_id.id:
            # Redirection vers la page de paiement (à adapter selon ton flow)
            return request.redirect('/shop/payment?order_id=%d' % order.id)
        else:
            # Si la commande est invalide, on revient à l'historique
            return request.redirect('/payment/history')


# 🔔 Contrôleur pour recevoir les notifications CinetPay
class CinetpayNotificationController(http.Controller):

    @http.route('/cinetpay/notify', type='json', auth='public', methods=['POST'], csrf=False)
    def cinetpay_notification(self, **kwargs):
        payload = request.jsonrequest
        _logger.info("📢 Notification CinetPay reçue : %s", payload)

        txn_id = payload.get('transaction_id')
        status = payload.get('status')

        # 📝 On recherche la commande liée à ce txn_id (qui est dans client_order_ref)
        order = request.env['sale.order'].sudo().search([('client_order_ref', '=', txn_id)], limit=1)

        if order:
            # On met à jour le statut CinetPay
            order.write({'cinetpay_status': status})

            if status == 'ACCEPTED':
                if order.state != 'sale':
                    order.action_confirm()
                _logger.info("✅ Paiement accepté pour la commande %s", order.name)

            elif status in ['REFUSED', 'CANCELLED']:
                if order.state != 'cancel':
                    order.action_cancel()
                _logger.info("❌ Paiement refusé ou annulé pour la commande %s", order.name)

        else:
            _logger.warning("❓ Aucun order trouvé pour txn_id %s", txn_id)

        return {'status': 'OK'}
