from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    point_of_sale_update_stock_quantities = fields.Selection([
            ('closing', 'At the session closing'),
            ('real', 'In real time'),
            ], default='real', string="Update quantities in stock",
            help="At the session closing: A picking is created for the entire session when it's closed\n In real time: Each order sent to the server create its own picking")
