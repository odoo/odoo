# -*- coding: utf-8 -*-
from odoo import fields, models

class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    local_url = fields.Char(compute='_local_url_get', string="Attachment URL")

    def _local_url_get(self):
        for attach in self:
            attach.local_url = attach.url if attach.url else '/web/image/%s?unique=%s' % (attach.id, attach.checksum)
