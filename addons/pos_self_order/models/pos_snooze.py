from odoo import api, models


class PosSnooze(models.Model):
    _inherit = 'pos.product.template.snooze'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._notify_snooze_updated()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._notify_snooze_updated()
        return result

    @api.ondelete(at_uninstall=False)
    def _notify_snooze_deleted(self):
        config = self.mapped('pos_config_id')
        payload = {'deleted_ids': [self.ids]}
        config._notify('SNOOZE_CHANGED', payload)

    def _notify_snooze_updated(self):
        snoozes_by_config = {}
        for snooze in self:
            snoozes_by_config.setdefault(snooze.pos_config_id, self.env['pos.product.template.snooze'])
            snoozes_by_config[snooze.pos_config_id] |= snooze

        for config, snoozes in snoozes_by_config.items():
            payload = {
                'records': {
                    'pos.product.template.snooze': self._load_pos_self_data_read(snoozes, config)
                }
            }
            config._notify('SNOOZE_CHANGED', payload)
