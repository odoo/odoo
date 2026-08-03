# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(IrHttp, self).session_info()
        if self.env.user._is_internal():
            config_parameter = self.env['ir.config_parameter'].sudo()
            res['max_time_between_keys_in_ms'] = config_parameter.get_int('barcode.max_time_between_keys_in_ms') or 150
            # Settings of the WebSocket based RFID scanners.
            res['rfid_ws_url'] = config_parameter.get_str('barcode.rfid_ws_url') or ''
            res['rfid_start_command'] = config_parameter.get_str('barcode.rfid_start_command') or ''
            res['rfid_stop_command'] = config_parameter.get_str('barcode.rfid_stop_command') or ''
            res['rfid_tag_extraction_regex'] = config_parameter.get_str('barcode.rfid_tag_extraction_regex') or ''
            res['rfid_trigger_keys'] = config_parameter.get_str('barcode.rfid_trigger_keys', 'F15')
        return res
