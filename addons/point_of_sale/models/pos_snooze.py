from odoo import api, fields, models
from odoo.fields import Datetime


class PosSnooze(models.Model):
    """Used to register snoozed records in a pos.session.

    If a pos.snooze record exists for a record type (e.g. product,
    self-ordering) for a specific pos_config, and the current time is between
    start_time and end_time, then that record is currently snoozed
    for that pos_config.
    """

    _name = 'pos.snooze'
    _description = "Snoozed records for Point of Sale"
    _order = "id desc"
    _inherit = ['pos.load.mixin']

    product_template_id = fields.Many2one('product.template', string='Product', ondelete="cascade")
    pos_config_id = fields.Many2one('pos.config', string='POS Config', ondelete="cascade", required=True, index=True)
    start_time = fields.Datetime(string='Start Time', required=True)
    end_time = fields.Datetime(string='End Time', required=False)
    type = fields.Selection(selection=[('product', 'Product')], string="Snoozed for?",
        required=True, default="product")

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['id', 'product_template_id', 'pos_config_id', 'start_time', 'end_time', 'type']
        return params

    def _cron_clean_records(self):
        now = Datetime.now()
        expired_snoozes = self.search([('end_time', '!=', False), ('end_time', '<', now)])
        expired_snoozes.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._notify_snooze_updated()
        return records

    @api.ondelete(at_uninstall=False)
    def _notify_snooze_deleted(self):
        self._notify_snooze_updated(is_deletion=True)

    def _notify_snooze_updated(self, is_deletion=False):
        snoozes_by_config = {}
        for snooze in self:
            snoozes_by_config.setdefault(snooze.pos_config_id, self.env['pos.snooze'])
            snoozes_by_config[snooze.pos_config_id] |= snooze

        for config, snoozes in snoozes_by_config.items():
            updated_records = None if is_deletion else snoozes
            deleted_ids = snoozes.ids if is_deletion else None
            self._sync_snoozes(config, updated_records=updated_records, deleted_record_ids=deleted_ids)

    @api.model
    def _sync_snoozes(self, config, updated_records=None, deleted_record_ids=None):
        config._notify_synchronisation(config.current_session_id.id,
                                       device_identifier=self.env.context.get('device_identifier', False),
                                       records={'pos.snooze': updated_records.ids} if updated_records else {},
                                       deleted_record_ids={'pos.snooze': deleted_record_ids} if deleted_record_ids else {})
