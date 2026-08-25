from odoo import models, fields

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    cinetpay_site_id = fields.Char(string="CinetPay Site ID")
    cinetpay_apikey = fields.Char(string="CinetPay API Key")

    code = fields.Selection(
        selection_add=[('cinetpay', 'CinetPay')],
        ondelete={'cinetpay': 'set default'}
    )


    def action_start_cinetpay_onboarding(self):
        # Ici tu peux mettre la logique d'onboarding, ou simplement passer pour l'instant
        return True

