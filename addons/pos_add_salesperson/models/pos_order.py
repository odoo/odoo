from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    sales_person_id = fields.Many2one('hr.employee', string="Salesperson", help="Employee responsible for the sale")
