# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    edi_format_id = fields.Many2one('account.edi.format')
