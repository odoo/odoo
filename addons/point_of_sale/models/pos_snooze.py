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
