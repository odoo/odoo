# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class PosConfig(models.Model):
    _inherit = 'pos.config'


    def _get_self_ordering_data(self):
        data = super()._get_self_ordering_data()
        data["config"]["epson_printer_ip"] = self.epson_printer_ip
        data["config"]["other_devices"] = self.other_devices
        return data
