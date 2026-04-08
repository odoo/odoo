# -*- coding: utf-8 -*-
from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    buyer_reference = fields.Char(help="'Code de Service' in Chorus PRO.")
    contract_reference = fields.Char(help="'Numéro de Marché' in Chorus PRO.")
    purchase_order_reference = fields.Char(help="'Engagement Juridique' in Chorus PRO.")

    def _get_alerts(self):
        alerts = super()._get_alerts()

        if self.peppol_move_state in ('ready', 'to_send', 'error') and self.env['account.edi.xml.ubl_bis3']._is_customer_behind_chorus_pro(self.partner_id):
            alerts['chorus_endpoint'] = {
                'level': 'warning',
                'message': _('Ensure all Chorus Pro fields are correctly filled before sending to Peppol'),
            }

        return alerts
