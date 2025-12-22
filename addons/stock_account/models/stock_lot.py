# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero


class StockLot(models.Model):
    _inherit = 'stock.lot'

    value_svl = fields.Float(compute='_compute_value_svl', compute_sudo=True)
    quantity_svl = fields.Float(compute='_compute_value_svl', compute_sudo=True)
    avg_cost = fields.Monetary(string="Average Cost", compute='_compute_value_svl', compute_sudo=True, currency_field='company_currency_id')
    total_value = fields.Monetary(string="Total Value", compute='_compute_value_svl', compute_sudo=True, currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', 'Valuation Currency', compute='_compute_value_svl', compute_sudo=True)
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'lot_id')
    standard_price = fields.Float(
        "Cost", company_dependent=True,
        digits='Product Price', groups="base.group_user",
        help="""Value of the lot (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders."""
    )

    @api.depends('stock_valuation_layer_ids', 'product_id.lot_valuated')
    @api.depends_context('to_date', 'company')
    def _compute_value_svl(self):
        """Compute totals of multiple svl related values"""
        self.value_svl = 0
        self.quantity_svl = 0
        self.avg_cost = 0
        self.total_value = 0
        self.company_currency_id = False
        lots = self.filtered(lambda l: l.product_id.lot_valuated)
        if not lots:
            return
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        domain = [
            *self.env['stock.valuation.layer']._check_company_domain(company_id),
            ('lot_id', 'in', lots.ids),
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain.append(('create_date', '<=', to_date))
        groups = self.env['stock.valuation.layer']._read_group(
            domain,
            groupby=['lot_id'],
            aggregates=['value:sum', 'quantity:sum'],
        )
        # Browse all lots and compute lots' quantities_dict in batch.
        group_mapping = {lot: aggregates for lot, *aggregates in groups}
        for lot in lots:
            value_sum, quantity_sum = group_mapping.get(lot._origin, (0, 0))
            value_svl = self.company_currency_id.round(value_sum)
            avg_cost = value_svl / quantity_sum if quantity_sum else 0
            lot.value_svl = value_svl
            lot.quantity_svl = quantity_sum
            lot.avg_cost = avg_cost
            lot.total_value = avg_cost * quantity_sum

    @api.model_create_multi
    def create(self, vals_list):
        lots = super().create(vals_list)
        for product, lots_by_product in lots.grouped('product_id').items():
            if product.lot_valuated:
                lots_by_product.filtered(lambda lot: not lot.standard_price).with_context(disable_auto_svl=True).write({
                    'standard_price': product.standard_price
                })
        return lots

    def write(self, vals):
        if 'standard_price' in vals and not self.env.context.get('disable_auto_svl'):
            self._change_standard_price(vals['standard_price'])
        return super().write(vals)

    def _change_standard_price(self, new_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        if self.product_id.filtered(lambda p: p.valuation == 'real_time') and not self.env['stock.valuation.layer'].has_access('read'):
            raise UserError(_("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        svl_vals_list = []
        company_id = self.env.company
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        rounded_new_price = float_round(new_price, precision_digits=price_unit_prec)
        for lot in self:
            if lot.product_id.cost_method not in ('standard', 'average'):
                continue
            quantity_svl = lot.sudo().quantity_svl
            if float_compare(quantity_svl, 0.0, precision_rounding=lot.product_id.uom_id.rounding) <= 0:
                continue
            value_svl = lot.sudo().value_svl
            value = company_id.currency_id.round((rounded_new_price * quantity_svl) - value_svl)
            if company_id.currency_id.is_zero(value):
                continue

            svl_vals = {
                'company_id': company_id.id,
                'product_id': lot.product_id.id,
                'description': _('Lot value manually modified (from %(old)s to %(new)s)', old=lot.standard_price, new=rounded_new_price),
                'value': value,
                'quantity': 0,
                'lot_id': lot.id,
            }
            svl_vals_list.append(svl_vals)
        layers = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
        layers._change_standart_price_accounting_entries(new_price)
        for product in self.with_context(disable_auto_svl=True).product_id:
            if product.cost_method == 'standard':
                continue
            if product.quantity_svl:
                product.standard_price = product.value_svl / product.quantity_svl

    # # -------------------------------------------------------------------------
    # # Actions
    # # -------------------------------------------------------------------------
    def action_revaluation(self):
        # Cannot hide the button in list view for non required field in groupby
        if not self:
            raise UserError(_("Select an existing lot/serial number to be reevaluated"))
        elif all(float_is_zero(layer.remaining_qty, precision_rounding=self.product_id.uom_id.rounding) for layer in self.stock_valuation_layer_ids):
            raise UserError(_("You cannot adjust the valuation of a layer with zero quantity"))
        self.ensure_one()
        ctx = dict(self._context, default_lot_id=self.id, default_company_id=self.env.company.id)
        return {
            'name': _("Lot/Serial number Revaluation"),
            'view_mode': 'form',
            'res_model': 'stock.valuation.layer.revaluation',
            'view_id': self.env.ref('stock_account.stock_valuation_layer_revaluation_form_view').id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'target': 'new'
        }

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        domain = [('lot_id', '=', self.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
        context = literal_eval(action['context'])
        context.update(self.env.context)
        context['no_at_date'] = True
        return dict(action, domain=domain, context=context)
