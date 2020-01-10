# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_it_transport_reason_id = fields.Selection([('sale', 'Sale'), ('repair', 'Repair')], string='Transport Reason')
    l10n_it_transport_method_id = fields.Selection([('sender', 'Sender'), ('recipient', 'Recipient'), ('courier', 'Courier service')], string='Transport Reason')
    l10n_it_parcels = fields.Integer(string="Parcels")
    l10n_it_volume = fields.Integer(string="Volume")
    l10n_it_size = fields.Text(string="Size")
    invoice_ids = fields.Many2many('account.move', string="Invoices")

    def report_name(self):
        for picking in self:
            a = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            n = picking.id
            progressive_number = ""
            while n:
                (n, m) = divmod(n, len(a))
                progressive_number = a[m] + progressive_number

            report_name = '%(country_code)s%(codice)s_%(progressive_number)s.xml' % {
                'country_code': picking.company_id.country_id.code,
                'codice': picking.company_id.l10n_it_codice_fiscale,
                'progressive_number': progressive_number.zfill(5),
                }
        return report_name
