# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api



class CrateBarcodeConfiguration(models.Model):
    _name = 'crate.barcode.configuration'
    _description = 'Crate Barcode Configuration.'

    name = fields.Char(string='Scan Crate Barcode')
    crate_status = fields.Selection([('available', 'Available'),
                                     ('not_available', 'Not Available'),],
                                    string='Crate Status', default='available')

    def action_set_available(self):
        """Change the crate status to available."""
        for record in self:
            if record.crate_status == 'not_available':
                record.crate_status = 'available'