# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockLot(models.Model):
    _inherit = 'stock.lot'

    lot_valuated = fields.Boolean(related='product_id.lot_valuated', readonly=True, store=False)
    avg_cost = fields.Monetary(string="Average Cost", currency_field='company_currency_id')
    total_value = fields.Monetary(string="Total Value", compute='_compute_value', compute_sudo=True, currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', 'Valuation Currency', compute='_compute_value', compute_sudo=True)
    standard_price = fields.Float(
        "Cost", company_dependent=True,
        digits='Product Price', groups="base.group_user",
        help="""Value of the lot (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders."""
    )

    @api.depends('product_id.lot_valuated')
    @api.depends_context('to_date', 'company')
    def _compute_value(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        at_date = self.env.context.get('to_date')

        for lot in self:
            if not lot.lot_valuated:
                lot.total_value = 0.0
                lot.avg_cost = 0.0
                continue

            qty_available = lot.product_qty
            if lot.product_id.cost_method == 'standard':
                lot.total_value = lot.standard_price * qty_available
            elif lot.product_id.cost_method == 'average':
                lot.total_value = lot.product_id._run_avco(at_date=at_date, lot=lot)[1]
            else:
                lot.total_value = lot.product_id._run_fifo(qty_available, at_date=at_date, lot=lot)
            lot.avg_cost = lot.total_value / qty_available if qty_available else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        lots = super().create(vals_list)
        for product, lots_by_product in lots.grouped('product_id').items():
            if product.lot_valuated:
                lots_by_product.filtered(lambda lot: not lot.standard_price).with_context(disable_auto_revaluation=True).write({
                    'standard_price': product.standard_price,
                })
        return lots

    def write(self, vals):
        if 'standard_price' in vals and not self.env.context.get('disable_auto_revaluation'):
            self._change_standard_price(vals['standard_price'])
        return super().write(vals)

    def _update_standard_price(self):
        # TODO: Add extra value and extra quantity kwargs to avoid total recomputation
        for lot in self:
            if lot.product_id.cost_method == 'standard':
                continue
            lot.with_context(disable_auto_revaluation=True).standard_price = lot.product_id._run_avco(lot=lot)[0]

    def _change_standard_price(self, new_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
<<<<<<< b5cd67ccaeaaa1179b4dc61a2492f13da765177f
||||||| 61cbad8a16395f268cb1712ddcf84de23b92ecf5
        if self.product_id.filtered(lambda p: p.valuation == 'real_time') and not self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
            raise UserError(_("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        svl_vals_list = []
        company_id = self.env.company
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        rounded_new_price = float_round(new_price, precision_digits=price_unit_prec)
=======
        if self.product_id.filtered(lambda p: p.valuation == 'real_time') and not self.env['stock.valuation.layer'].has_access('read'):
            raise UserError(_("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        svl_vals_list = []
        company_id = self.env.company
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        rounded_new_price = float_round(new_price, precision_digits=price_unit_prec)
>>>>>>> 800ce0091e897497ab567344b748fb371863c6f3
        for lot in self:
            if lot.product_id.cost_method != 'average' or lot.standard_price == new_price:
                continue
            product = lot.product_id
            self.env['product.value'].create({
                'product_id': product.id,
                'lot_id': lot.id,
                'value': new_price,
                'company_id': product.company_id or self.env.company.id,
                'date': fields.Datetime.now(),
                'description': _('%(lot)s price update from %(old_price)s to %(new_price)s by %(user)s',
                    lot=lot.name, old_price=product.standard_price, new_price=new_price, user=self.env.user.name)
            })

    # # -------------------------------------------------------------------------
    # # Actions
    # # -------------------------------------------------------------------------
    def action_revaluation(self):
        # Cannot hide the button in list view for non required field in groupby
        if not self:
            raise UserError(_("Select an existing lot/serial number to be reevaluated"))
        elif all(self.product_id.uom_id.is_zero(lot.product_qty) for lot in self):
            raise UserError(_("You cannot adjust the valuation of a layer with zero quantity"))
        self.ensure_one()
        ctx = dict(self.env.context, default_lot_ids=self.ids, default_company_id=self.env.company.id)
        return {
            'name': _('Lot/Serial number Revaluation - %s', self.product_id.display_name),
            'view_mode': 'form',
            'res_model': 'stock.valuation.layer.revaluation',
            'view_id': self.env.ref('stock_account.stock_valuation_layer_revaluation_form_view').id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'target': 'new'
        }
