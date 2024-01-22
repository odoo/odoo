from odoo import api, models, fields


class DistributionOrder(models.Model):
    _name = "distribution.order"
    _description = "Distribution"

    name = fields.Char(string='Name', required=True, copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('distribution.order'))
    contract_id = fields.Many2one('contract', string='Contract', required=True, ondelete='cascade')
    order_type = fields.Selection(related="contract_id.position", string="Position", store=True)
    delivery_point_id = fields.Many2one('border', related='contract_id.parent_contract_id.delivery_point_id',
                                        string='Delivery Point', store=True)
    power_date = fields.Date(string='Power Date', required=True)
    power_hour = fields.Integer(string='Power Hour', )
    total_power = fields.Float(string='Total Power', compute='_compute_power_balance', )
    distributed_power = fields.Float(string='Distributed Power', compute='_compute_power_balance', )
    actual_power = fields.Float(string='Actual Power', compute='_compute_power_balance', )
    distribution_line_ids = fields.One2many('distribution.order.line', 'distribution_id', string='Distribution Lines')

    def _compute_power_balance(self):
        for record in self:
            total_power = 0.0
            # get all active contracts for this border to compute total power available
            contracts = self.env["contract"].search([
                ("delivery_point_id", "=", record.delivery_point_id.id),
                ("status", "=", "executing"),
                ("position", "=", record.order_type)
            ])
            if contracts:
                total_power = sum(contracts.loadshape_details_ids.filtered(
                    lambda l: l.powerdate == record.power_date and l.powerhour == record.power_hour).mapped("power"))
            record.total_power = total_power
            record.distributed_power = sum(record.distribution_line_ids.mapped("power"))
            record.actual_power = record.total_power - record.distributed_power


class DistributionOrderLine(models.Model):
    _name = "distribution.order.line"
    _description = "Distribution Line"
    _order = 'distribution_id, power_date, power_hour'
    # _rec_names_search = ['contract_id.name', 'distribution_id.name']

    name = fields.Text(string='Description', compute='_compute_name', store=True)
    contract_id = fields.Many2one('contract', related="distribution_id.contract_id", string='Contract')
    order_type = fields.Selection(related="contract_id.position", string="Position", store=True)
    contract_delivery_point_id = fields.Many2one('border', related="contract_id.delivery_point_id",
                                                 string='Contract Delivery Point')
    delivery_point_id = fields.Many2one('border', string='Delivery Point', required=True)
    distribution_id = fields.Many2one('distribution.order', string='Distribution', ondelete='cascade',
                                      index=True, copy=False)
    power_date = fields.Date(string='Power Date', related="distribution_id.power_date", store=True)
    power_hour = fields.Integer(string='Power Hour', )
    total_power = fields.Float(string='Total Power')
    actual_power = fields.Float(string='Actual Power')
    power = fields.Float("Power")

    @api.depends('contract_id', 'power_date', 'power_hour', 'delivery_point_id')
    def _compute_name(self):
        for line in self:
            name = False
            if line.delivery_point_id:
                name = line.delivery_point_id.name + " - " + str(line.power)
            line.name = name

    def _compute_power_balance_line(self):
        for record in self:
            total_power = 0.0
            # get all active contracts for this border to compute total power available
            contracts = self.env["contract"].search([
                ("delivery_point_id", "=", record.delivery_point_id.id),
                ("status", "=", "executing"),
                ("position", "=", record.order_type)
            ])
            if contracts:
                total_power = sum(contracts.loadshape_details_ids.filtered(
                    lambda l: l.powerdate == record.power_date and l.powerhour == record.power_hour).mapped("power"))

            record.total_power = total_power
            record.distributed_power = sum(record.distribution_line_ids.mapped("value"))
            record.actual_power = record.total_power - record.distributed_power

    @api.onchange('distribution_id', 'distribution_id.power_hour')
    def _get_power_hour(self):
        for rec in self:
            if rec.distribution_id and rec.distribution_id.power_hour:
                rec.power_hour = rec.distribution_id.power_hour
