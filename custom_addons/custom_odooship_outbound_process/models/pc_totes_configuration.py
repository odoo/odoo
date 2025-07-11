# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class CrateBarcodeConfiguration(models.Model):
    _name = 'pc.container.barcode.configuration'
    _description = 'PC container Barcode Configuration.'

    name = fields.Char(string='Container Barcode')
    pc_container_status = fields.Selection([('release', 'Release'),
                                     ('occupied', 'Occupied'),],
                                    string='PC container Status', default='release')
    site_code_id = fields.Many2one('site.code.configuration',
                                   required=True,
                                   string='Site Code',
                                   store=True)
    warehouse_id = fields.Many2one(related='site_code_id.warehouse_id', store=True)

    def action_set_release(self):
        """Change the crate status to available."""
        for record in self:
            if record.pc_container_status == 'occupied':
                record.pc_container_status = 'release'

    def action_set_occupied(self):
        """Change the crate status to available."""
        for record in self:
            if record.pc_container_status == 'release':
                record.pc_container_status = 'occupied'