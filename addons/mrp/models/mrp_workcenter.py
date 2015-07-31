# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _

#----------------------------------------------------------
# Work Centers
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource':"resource_id"}
    note = fields.Text(string='Description', help="Description of the Work Center. Explain here what's a cycle according to this Work Center.")
    capacity_per_cycle = fields.Float(string='Capacity per Cycle', default=1.0, help="Number of operations this Work Center can do in parallel. If this Work Center represents a team of 5 workers, the capacity per cycle is 5.")
    time_cycle = fields.Float(string='Time for 1 cycle (hour)', help="Time in hours for doing one cycle.")
    time_start = fields.Float(string='Time before prod.', help="Time in hours for the setup.")
    time_stop = fields.Float(string='Time after prod.', help="Time in hours for the cleaning.")
    costs_hour = fields.Float(string='Cost per hour', help="Specify Cost of Work Center per hour.")
    costs_hour_account_id = fields.Many2one('account.analytic.account', string='Hour Account', domain=[('type', '!=', 'view')],
        help="Fill this only if you want automatic analytic accounting entries on production orders.")
    costs_cycle = fields.Float(string='Cost per cycle', help="Specify Cost of Work Center per cycle.")
    costs_cycle_account_id = fields.Many2one('account.analytic.account', string='Cycle Account', domain=[('type', '!=', 'view')],
            help="Fill this only if you want automatic analytic accounting entries on production orders.")
    costs_journal_id = fields.Many2one('account.analytic.journal', string='Analytic Journal')
    costs_general_account_id = fields.Many2one('account.account', string='General Account', domain=[('deprecated', '=', False)])
    resource_id = fields.Many2one('resource.resource', string='Resource', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Work Center Product', help="Fill this product to easily track your production costs in the analytic accounting.")
    resource_type = fields.Selection([('user', 'Human'), ('material', 'Material')], string='Resource Type', required=True, default='material')

    @api.onchange('product_id')
    def on_change_product_cost(self):
        if self.product_id:
            self.costs_hour = self.product_id.standard_price

    @api.multi
    @api.constrains('capacity_per_cycle')
    def _check_capacity_per_cycle(self):
        for obj in self:
            if obj.capacity_per_cycle <= 0.0:
                raise ValueError(_('The capacity per cycle must be strictly positive.'))
