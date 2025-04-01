from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SalesRoute(models.Model):
    _name = 'sales.route'
    _description = 'Sales Route Management'
    
    name = fields.Char(string="Route Name", required=True)
    region = fields.Char(string="Region")
    sales_rep_id = fields.Many2one('res.users', string="Assigned Sales Rep", required=True)
    customers = fields.Many2many('res.partner', string="Customers on Route")

    @api.constrains('sales_rep_id')
    def _check_unique_rep(self):
        """ Ensure one sales rep is not assigned multiple overlapping routes """
        routes = self.search([])
        for record in self:
            existing_routes = self.env['sales.route'].search([
                ('sales_rep_id', '=', record.sales_rep_id.id),
                ('id', '!=', record.id)
            ])
            if existing_routes:
                raise ValidationError(f"Sales Rep {record.sales_rep_id.name} is already assigned to another route.")
         _logger.info("Sales Route cron job executed successfully!")