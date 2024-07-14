# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ShiprocketCourier(models.Model):
    _name = 'shiprocket.courier'
    _description = 'Shiprocket Courier'
    _order = 'name'

    name = fields.Char('Service Name', readonly=True)
    courier_code = fields.Integer('Courier Code', readonly=True)
    shiprocket_email = fields.Char(string='Shiprocket Email')
