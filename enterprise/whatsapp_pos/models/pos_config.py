# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    whatsapp_enabled = fields.Boolean('WhatsApp Enabled', default=False)
    receipt_template_id = fields.Many2one('whatsapp.template', string="Receipt template", domain=[('model', '=', 'pos.order'), ('status', '=', 'approved')])
    invoice_template_id = fields.Many2one('whatsapp.template', string="Invoice template", domain=[('model', '=', 'account.move'), ('status', '=', 'approved')])
