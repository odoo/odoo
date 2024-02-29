from odoo import api, fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_data_params(self, config_id):
        res = super()._load_data_params(config_id)
        res['pos.payment.method']['fields'] += ['delivery_payment_method']
        return res
    
    def load_data(self, models_to_load, only_data=False):
        res = super().load_data(models_to_load, only_data)
        if not only_data:
            res['custom']['delivery_order_count'] = self.config_id.get_delivery_order_count()
        return res