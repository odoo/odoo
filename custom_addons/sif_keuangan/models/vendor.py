# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SifVendor(models.Model):
    _name = 'sif.vendor'
    _description = 'Master Vendor'
    _order = 'name asc'

    name = fields.Char(string='Nama Vendor', required=True)
    code = fields.Char(string='Kode Vendor', required=True, copy=False, default='Baru')
    phone = fields.Char(string='Telepon')
    email = fields.Char(string='Email')
    address = fields.Text(string='Alamat')
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'Baru') == 'Baru':
                vals['code'] = self.env['ir.sequence'].next_by_code('sif.vendor') or 'Baru'
        return super().create(vals_list)
