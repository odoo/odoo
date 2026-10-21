# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    einvoice_vat_info = fields.Text(string='Thông tin MST')
    einvoice_vat = fields.Char(string='Mã số thuế')
    einvoice_name = fields.Char(string='Tên khách hàng')
    einvoice_buyer_name = fields.Char(string='Tên đơn vị')
    einvoice_partner_id = fields.Char(string='CCCD')
    einvoice_address = fields.Text(string='Địa chỉ')
