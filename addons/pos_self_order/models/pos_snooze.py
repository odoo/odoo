# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosSnooze(models.Model):
    _inherit = 'pos.snooze'

    type = fields.Selection(selection_add=[('self-ordering', 'Self Order Service')], ondelete={'self-ordering': 'cascade'})

    @api.model
    def _sync_snoozes(self, config, updated_records=None, deleted_record_ids=None):
        super()._sync_snoozes(config, updated_records, deleted_record_ids)
        payload = {
            'deleted_ids': deleted_record_ids if deleted_record_ids else [],
            'records':  self._load_pos_self_data_read(updated_records, config) if updated_records else [],
        }
        config._notify('SNOOZE_CHANGED', payload)
