# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    trigger_ids = fields.One2many('iot.trigger', 'workcenter_id', string="Triggers")


class IotTrigger(models.Model):
    _name = 'iot.trigger'
    _description = 'IOT Trigger'
    _order = 'sequence'

    sequence = fields.Integer(default=1)
    device_id = fields.Many2one('iot.device', 'Device', required=True, domain="[('type', '=', 'keyboard')]")
    key = fields.Char('Key')
    workcenter_id = fields.Many2one('mrp.workcenter')
    action = fields.Selection([('picture', 'Take Picture'),
                               ('skip', 'Skip'),
                               ('pause', 'Pause'),
                               ('prev', 'Previous'),
                               ('next', 'Next'),
                               ('validate', 'Validate'),
                               ('cloMO', 'Close MO'),
                               ('cloWO', 'Close WO'),
                               ('finish', 'Finish'),
                               ('record', 'Record Production'),
                               ('cancel', 'Cancel'),
                               ('print-op', 'Print Operation'),
                               ('print-slip', 'Print Delivery Slip'),
                               ('print', 'Print Labels'),
                               ('pack', 'Pack'),
                               ('scrap', 'Scrap'),])

class IoTDevice(models.Model):
    _inherit = "iot.device"

    trigger_ids = fields.One2many('iot.trigger', 'device_id')
