from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['pos.delivery.provider']
        return data

    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        result = super().close_session_from_ui(bank_payment_method_diff_pairs)
        if self.config_id.module_pos_urban_piper:
            self.config_id.update_store_status(status=False)  # api request for updating status at urban piper
        self.config_id.set_urban_piper_provider_states({})
        return result

    def delete_opening_control_session(self):
        self.config_id.set_urban_piper_provider_states({})
        return super().delete_opening_control_session()

    def get_closing_control_data(self):
        data = super().get_closing_control_data()
        orders = self._get_closed_orders()
        urban_piper_payment_method_ids = self.config_id.urbanpiper_payment_methods_ids
        data_non_cash_methods = [pm['id'] for pm in data.get('non_cash_payment_methods')] if data.get('non_cash_payment_methods') else []
        urban_piper_non_cash_payments_grouped_by_method_id = {pm: orders.payment_ids.filtered(lambda p: p.payment_method_id == pm) for pm in urban_piper_payment_method_ids if pm.id not in data_non_cash_methods}
        if data.get('non_cash_payment_methods'):
            non_cash_methods = [
                {
                    'name': pm.name,
                    'amount': sum(urban_piper_non_cash_payments_grouped_by_method_id[pm].mapped('amount')),
                    'number': len(urban_piper_non_cash_payments_grouped_by_method_id[pm]),
                    'id': pm.id,
                    'type': pm.type,
                }
                for pm in urban_piper_non_cash_payments_grouped_by_method_id
            ]
            data['non_cash_payment_methods'].extend(non_cash_methods)
        return data
