# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _

# ----------------------------------------------------------
# Work Centers
# ----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle


class WorkCenter(models.Model):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource': 'resource_id'}

    active = fields.Boolean('Active', default=True)
    note = fields.Text(
        'Description',
        help="Description of the Work Center. Explain here what's a cycle according to this Work Center.")
    capacity_per_cycle = fields.Float(
        'Capacity per Cycle', default=1.0,
        help="Number of operations this Work Center can do in parallel. If this Work "
             "Center represents a team of 5 workers, the capacity per cycle is 5.")
    time_cycle = fields.Float(
        'Time for 1 cycle (hour)', help="Time in hours for doing one cycle.")
    time_start = fields.Float(
        'Time before prod.', help="Time in hours for the setup.")
    time_stop = fields.Float(
        'Time after prod.', help="Time in hours for the cleaning.")
    costs_hour = fields.Float(
        'Cost per hour', help="Specify Cost of Work Center per hour.")
    costs_hour_account_id = fields.Many2one(
        'account.analytic.account', 'Hour Account',
        help="Fill this only if you want automatic analytic accounting entries on production orders.")
    costs_cycle = fields.Float(
        'Cost per cycle', help="Specify Cost of Work Center per cycle.")
    costs_cycle_account_id = fields.Many2one(
        'account.analytic.account', 'Cycle Account',
        help="Fill this only if you want automatic analytic accounting entries on production orders.")
    costs_general_account_id = fields.Many2one(
        'account.account', 'General Account',
        domain=[('deprecated', '=', False)])
    resource_id = fields.Many2one(
        'resource.resource', 'Resource',
        ondelete='cascade', required=True)
    product_id = fields.Many2one(
        'product.product', 'Work Center Product',
        help="Fill this product to easily track your production costs in the analytic accounting.")

    @api.multi
    @api.constrains('capacity_per_cycle')
    def _check_capacity_per_cycle(self):
        if any(workcenter.capacity_per_cycle <= 0.0 for workcenter in self):
            raise exceptions.UserError(_('The capacity per cycle must be strictly positive.'))

    @api.onchange('product_id')
    def on_change_product_id(self):
        if self.product_id:
            self.costs_hour = self.product_id.standard_price
