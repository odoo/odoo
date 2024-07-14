# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class EasypostService(models.Model):
    _name = 'easypost.service'
    _description = 'Easypost Service'

    name = fields.Char('Service Level Name', index=True)
    easypost_carrier = fields.Char('Carrier Prefix', index=True)

    def _require_residential_address(self):
        services = [('FedEx', 'GROUND_HOME_DELIVERY')]
        return (self.easypost_carrier, self.name) in services

    def _get_service_specific_options(self):
        options = {}
        if (self.easypost_carrier, self.name) in [('FedEx', 'GROUND_HOME_DELIVERY')]:
            options['saturday_delivery'] = False
        return options
