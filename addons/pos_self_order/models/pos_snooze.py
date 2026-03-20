from odoo import api, models


class PosSnooze(models.Model):
    _inherit = 'pos.product.template.snooze'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            # Notify open self orders that a product is now snoozed
            record._notify_availability_updated()

        return records

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            record._notify_availability_updated()
        return res

    @api.ondelete(at_uninstall=False)
    def _notify_availability_deleted(self):
        config = self.mapped('pos_config_id')
        payload = {'deleted': [self.ids]}
        config._notify('SNOOZE_CHANGED', payload)

    def _notify_availability_updated(self):
        config = self.pos_config_id
        payload = {'pos.product.template.snooze': self._load_pos_self_data_read(self, config)}
        config._notify('SNOOZE_CHANGED', payload)
