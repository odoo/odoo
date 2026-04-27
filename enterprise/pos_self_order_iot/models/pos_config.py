import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    available_iot_box_ids = fields.One2many(
        'iot.box',
        'pos_id',
        string='Available IoT Boxes',
        domain="[('can_be_kiosk', '=', True)]",
        required=True,
    )

    def _get_kitchen_printer(self):
        res = super()._get_kitchen_printer()
        for printer in self.printer_ids:
            if printer.device_identifier:
                res[printer.id]["device_identifier"] = printer.device_identifier
        return res

    def _load_self_data_models(self):
        models = super()._load_self_data_models()
        models += ['iot.device']
        return models

    def get_available_iot_box_ids(self):
        self.available_iot_box_ids = self.env['iot.box'].search([('can_be_kiosk', '=', True)])
        return self.available_iot_box_ids.read(['id', 'name', 'ip_url'])

    @api.model
    def _load_pos_self_data_fields(self, pos_config_id):
        fields = super()._load_pos_self_data_fields(pos_config_id)
        return fields + ['available_iot_box_ids', 'iface_printer_id']
