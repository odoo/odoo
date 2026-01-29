from odoo import models, api

class PosPreset(models.Model):
    _inherit = "pos.preset"

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        """
        Dynamically filter available presets for Self-Order.
        If 'Accept Remote Orders' is disabled, hide 'delivery' options.
        """
        domain = super()._load_pos_self_data_domain(data, config)
        
        # If accept_remote_orders is False, we filter out 'delivery' service_at
        if not config.accept_remote_orders:
            # We wrap the existing domain with an AND condition to exclude delivery
            domain = ['&'] + domain + [('service_at', '!=', 'delivery')]
            
        return domain
