from odoo import models, fields, api

class SalesVisit(models.Model):
    _name = 'sales.visit'
    _description = 'Sales Visit'

    customer_id = fields.Many2one('res.partner', string="Customer", required=True)
    sales_rep_id = fields.Many2one('res.users', string="Sales Rep", required=True, default=lambda self: self.env.user)
    scheduled_date = fields.Datetime(string="Scheduled Visit")
    check_in_time = fields.Datetime(string="Check-in Time")
    check_out_time = fields.Datetime(string="Check-out Time")
    visit_notes = fields.Text(string="Visit Notes")

    def check_in(self):
        """ Mark check-in time when sales rep visits the customer """
        self.check_in_time = fields.Datetime.now()

    def check_out(self):
        """ Mark check-out time when sales rep leaves the customer """
        self.check_out_time = fields.Datetime.now()