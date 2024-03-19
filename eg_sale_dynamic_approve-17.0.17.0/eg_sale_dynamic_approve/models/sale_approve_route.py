from odoo import models, fields


class SaleApproveRoute(models.Model):
    _name = "sale.approve.route"
    _description = "Sale Approve Route"

    sale_id = fields.Many2one(comodel_name="sale.order", string="Sale")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Approver")
    role = fields.Char(string="Role")
    state = fields.Selection(selection=[('draft', 'Pending'), ('done', 'To Approve'), ('reject', 'Disapprove')], string='Status', default='draft')