# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import groupby


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    value = fields.Monetary('Value', compute='_compute_value', groups='stock.group_stock_manager')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', groups='stock.group_stock_manager')
    accounting_date = fields.Date(
        'Accounting Date',
        help="Date at which the accounting entries will be created"
             " in case of automated inventory valuation."
             " If empty, the inventory date will be used.")
    cost_method = fields.Selection(
        string="Cost Method",
        selection=[
            ('standard', "Standard Price"),
            ('fifo', "First In First Out (FIFO)"),
            ('average', "Average Cost (AVCO)"),
        ],
        compute='_compute_cost_method',
    )

    @api.depends_context('company')
    @api.depends('product_categ_id.property_cost_method')
    def _compute_cost_method(self):
        for quant in self:
            quant.cost_method = (
                quant.product_categ_id.with_company(
                    quant.company_id
                ).property_cost_method
                or (quant.company_id or self.env.company).cost_method
            )

    @api.model_create_multi
    def create(self, vals_list):
        if any(val.get('accounting_date') for val in vals_list):
            return super().create(vals_list)

        product_ids = {val["product_id"] for val in vals_list}

        tracked_products = self.env["product.product"].search([
            ("id", "in", product_ids),
            ("tracking", "in", ["lot", "serial"])
        ])
        tracked_product_ids = set(tracked_products.ids)

        tracked_quants = [q for q in vals_list if q["product_id"] in tracked_product_ids]
        untracked_quants = [q for q in vals_list if q["product_id"] not in tracked_product_ids]

        if tracked_quants:
            tracked_product_ids = {q["product_id"] for q in tracked_quants}
            location_ids = {q["location_id"] for q in tracked_quants}

            domain = [
                ('product_id', 'in', list(tracked_product_ids)),
                ('location_id', 'in', list(location_ids)),
                ('accounting_date', '<', fields.Date.today()),
            ]
            query = self._search(domain, order='accounting_date desc')
            nearest_date_quants = self.env.execute_query(
                query.select('product_id', 'location_id', 'accounting_date')
            )

            latest_accounting_dates = {}
            for product_id, location_id, accounting_date in nearest_date_quants:
                key = (product_id, location_id)
                latest_accounting_dates[key] = max(latest_accounting_dates.get(key, accounting_date), accounting_date)

            for quant in tracked_quants:
                key = (quant["product_id"], quant["location_id"])
                if key in latest_accounting_dates:
                    quant["accounting_date"] = latest_accounting_dates[key]
        return super().create(tracked_quants + untracked_quants)

    @api.model
    def _should_exclude_for_valuation(self):
        """
        Determines if a quant should be excluded from valuation based on its ownership.
        :return: True if the quant should be excluded from valuation, False otherwise.
        """
        self.ensure_one()
        return self.owner_id and self.owner_id != self.company_id.partner_id

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    def _compute_value(self):
        """ (Product.value_svl / Product.quantity_svl) * quant.quantity, i.e. average unit cost * on hand qty
        """
        self.fetch(['company_id', 'location_id', 'owner_id', 'product_id', 'quantity', 'lot_id'])
        self.value = 0
        for quant in self:
            if not quant.location_id or not quant.product_id or\
                    not quant.location_id._should_be_valued() or\
                    quant._should_exclude_for_valuation() or\
                    float_is_zero(quant.quantity, precision_rounding=quant.product_id.uom_id.rounding):
                continue
            if quant.product_id.lot_valuated:
                quantity = quant.lot_id.with_company(quant.company_id).quantity_svl
                value_svl = quant.lot_id.with_company(quant.company_id).value_svl
            else:
                quantity = quant.product_id.with_company(quant.company_id).quantity_svl
                value_svl = quant.product_id.with_company(quant.company_id).value_svl
            if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                continue
            quant.value = quant.quantity * value_svl / quantity

    def _read_group_select(self, aggregate_spec, query):
        # flag value as aggregatable, and manually sum the values from the
        # records in the group
        if aggregate_spec == 'value:sum':
            return super()._read_group_select('id:recordset', query)
        return super()._read_group_select(aggregate_spec, query)

    def _read_group_postprocess_aggregate(self, aggregate_spec, raw_values):
        if aggregate_spec == 'value:sum':
            column = super()._read_group_postprocess_aggregate('id:recordset', raw_values)
            return (sum(records.mapped('value')) for records in column)
        return super()._read_group_postprocess_aggregate(aggregate_spec, raw_values)

    def _apply_inventory(self):
        for accounting_date, inventory_ids in groupby(self, key=lambda q: q.accounting_date):
            inventories = self.env['stock.quant'].concat(*inventory_ids)
            if accounting_date:
                super(StockQuant, inventories.with_context(force_period_date=accounting_date))._apply_inventory()
                inventories.accounting_date = False
            else:
                super(StockQuant, inventories)._apply_inventory()

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False):
        res_move = super()._get_inventory_move_values(qty, location_id, location_dest_id, package_id, package_dest_id)
        if not self.env.context.get('inventory_name'):
            force_period_date = self.env.context.get('force_period_date', False)
            if force_period_date:
                res_move['name'] += _(' [Accounted on %s]', force_period_date)
        return res_move

    @api.model
    def _get_inventory_fields_write(self):
        """ Returns a list of fields user can edit when editing a quant in `inventory_mode`."""
        res = super()._get_inventory_fields_write()
        res += ['accounting_date']
        return res
