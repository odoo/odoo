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
                               ('SKIP', 'Skip'),
                               ('PAUS', 'Pause'),
                               ('PREV', 'Previous'),
                               ('NEXT', 'Next'),
                               ('VALI', 'Validate'),
                               ('CLMO', 'Close MO'),
                               ('CLWO', 'Close WO'),
                               ('FINI', 'Finish'),
                               ('RECO', 'Record Production'),
                               ('CANC', 'Cancel'),
                               ('PROP', 'Print Operation'),
                               ('PRSL', 'Print Delivery Slip'),
                               ('PRNT', 'Print Labels'),
                               ('PACK', 'Pack'),
                               ('SCRA', 'Scrap')])

class IoTDevice(models.Model):
    _inherit = "iot.device"

    trigger_ids = fields.One2many('iot.trigger', 'device_id')
