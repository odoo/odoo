# payment_cinetpay/controllers/main.py

from odoo import http
from odoo.http import request
import uuid

class CinetPayPOSController(http.Controller):

    @http.route(['/payment/cinetpay/pos/pay'], type='http', auth='public')
    def pay_with_cinetpay_pos(self, amount=0.0, client_id=None, **kwargs):
        """
        Ce contrôleur est appelé depuis le POS. Il redirige vers l'interface CinetPay.
        """
        # Charger les credentials depuis ir.config_parameter
        site_id = request.env['ir.config_parameter'].sudo().get_param('cinetpay.site_id')
        apikey = request.env['ir.config_parameter'].sudo().get_param('cinetpay.apikey')
        currency = "XOF"
        trans_id = str(uuid.uuid4())  # Générer un ID unique

        # Créer un lien de redirection vers CinetPay
        redirect_url = f"https://checkout.cinetpay.com/?transaction_id={trans_id}&amount={amount}&currency={currency}&site_id={site_id}&apikey={apikey}&description=Paiement POS Odoo&customer_id={client_id}&notify_url=https://ton_domaine.com/payment/cinetpay/pos/notify"

        # (optionnel) enregistrer une transaction dans Odoo (tu peux créer un modèle `pos.payment.cinetpay` si besoin)

        # Rediriger vers CinetPay
        return request.redirect(redirect_url)
