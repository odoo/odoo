from odoo import api, models


class PosSnooze(models.Model):
    _inherit = 'pos.product.template.snooze'

    @api.model
    def _sync_snoozes(self, config, updated_records=None, deleted_record_ids=None):
        super()._sync_snoozes(config, updated_records, deleted_record_ids)
        payload = {
            'deleted_ids': deleted_record_ids if deleted_record_ids else [],
            'records':  self._load_pos_self_data_read(updated_records, config) if updated_records else [],
        }
        config._notify('SNOOZE_CHANGED', payload)
