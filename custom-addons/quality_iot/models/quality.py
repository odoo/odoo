# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class QualityPoint(models.Model):
    _inherit = "quality.point"

    device_id = fields.Many2one('iot.device', ondelete='restrict', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")


class QualityCheck(models.Model):
    _inherit = "quality.check"

    ip = fields.Char(related='point_id.device_id.iot_id.ip')
    identifier = fields.Char(related='point_id.device_id.identifier')
    device_name = fields.Char(related='point_id.device_id.name', size=30, string='Device Name: ')
