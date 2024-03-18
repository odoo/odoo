# -*- coding: utf-8 -*-
from odoo import fields, models


class DeviceServiceTag(models.Model):
    _name = "device.service.tag"
    _description = "Device Service Tag"

    # Use the service_tag_id field as the default 'name' field
    _rec_name = "service_tag_id"

    service_tag_id = fields.Char("Service Tag ID", required=True)
    authentication_token = fields.Char(required=True)
