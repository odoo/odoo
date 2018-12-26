# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_it_transport_reason_id = fields.Selection([('sale', 'Sale'), ('repair', 'Repair')], string='Transport Reason')
    l10n_it_transport_method_id = fields.Selection([('sender', 'Sender'), ('recipient', 'Recipient'), ('courier', 'Courier service')], string='Transport Reason')
    l10n_it_parcels = fields.Integer(string="parcels")
    l10n_it_volume = fields.Integer(string="volume")
    l10n_it_size = fields.Text(string="size")
