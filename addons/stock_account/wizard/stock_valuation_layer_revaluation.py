# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockValuationLayerRevaluation(models.TransientModel):
    _name = 'stock.valuation.layer.revaluation'
    _description = "Wizard model to reavaluate a stock inventory for a product"
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        context = self.env.context
        if context.get('active_model') == 'stock.lot':
            # coming from action button where lot is group_by in valuation layer list view.
            lot = self.env['stock.lot'].browse(context.get('active_ids')).exists()
            if lot:
                res['product_id'] = lot.product_id.id
                res['lot_ids'] = [(6, 0, lot.ids)]

        if context.get('active_model') == 'stock.valuation.layer':
            # coming from action button "Adjust Valuation" in valuation layer list view.
            active_ids = context.get('active_ids')
            layers = self.env['stock.valuation.layer'].browse(active_ids).exists()
            product = layers.product_id
            if len(product) > 1:
                raise UserError(_("You cannot revalue multiple products at once"))
            if any(product.uom_id.is_zero(layer.remaining_qty) for layer in layers):
                raise UserError(_("You cannot adjust the valuation of a layer with zero quantity"))
            res['adjusted_layer_ids'] = active_ids
            res['product_id'] = product.id
            if product.lot_valuated:
                res['lot_ids'] = [(6, 0, layers.lot_id.ids)]
        product = self.env['product.product'].browse(res.get('product_id'))

        if context.get('active_model') == 'product.product':
            # coming from action button where product is group_by in valuation layer list view.
            if product.lot_valuated:
                res['lot_ids'] = [(6, 0, product.stock_valuation_layer_ids.filtered(lambda layer: layer.remaining_qty != 0).lot_id.ids)]

        if 'product_id' in fields:
            if not product:
                raise UserError(_("You cannot adjust valuation without a product"))
            if product.cost_method == 'standard':
                raise UserError(_("You cannot revalue a product with a standard cost method."))
            if product.quantity_svl <= 0:
                raise UserError(_("You cannot revalue a product with an empty or negative stock."))
            if 'account_journal_id' not in res and 'account_journal_id' in fields and product.valuation == 'real_time':
                accounts = product.product_tmpl_id.get_product_accounts()
                res['account_journal_id'] = accounts['stock_journal'].id
        return res

    company_id = fields.Many2one('res.company', "Company", readonly=True, required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', "Currency", related='company_id.currency_id', required=True)

    adjusted_layer_ids = fields.Many2many('stock.valuation.layer', string="Valuation Layers", help="Valuations layers being adjusted")
    product_id = fields.Many2one('product.product', "Related product", required=True, check_company=True)
    # Only filled when using lot_valuated on product.template
    lot_ids = fields.Many2many('stock.lot', readonly=True, check_company=True, help="All concerned lot/serial number")
    property_valuation = fields.Selection(related='product_id.valuation')
    product_uom_name = fields.Char("Unit", related='product_id.uom_id.name')
    current_value_svl = fields.Float("Current Value", compute='_compute_current_value_svl')
    current_quantity_svl = fields.Float("Current Quantity", compute='_compute_current_value_svl')

    added_value = fields.Monetary("Added value", required=True)
    added_value_by_qty = fields.Monetary("New adjusted value per unit", compute='_compute_new_value')

    new_value = fields.Monetary("New value", compute='_compute_new_value')
    new_value_by_qty = fields.Monetary("New value by quantity", compute='_compute_new_value')
    reason = fields.Char("Reason", help="Reason of the revaluation")

    account_journal_id = fields.Many2one('account.journal', "Journal", check_company=True)
    account_id = fields.Many2one('account.account', "Counterpart Account", check_company=True)
    date = fields.Date("Accounting Date")

    @api.depends('current_value_svl', 'current_quantity_svl', 'added_value')
    def _compute_new_value(self):
        for reval in self:
            reval.new_value = reval.current_value_svl + reval.added_value
            if not self.product_id.uom_id.is_zero(reval.current_quantity_svl):
                reval.new_value_by_qty = reval.new_value / reval.current_quantity_svl
                reval.added_value_by_qty = reval.added_value / reval.current_quantity_svl
            else:
                reval.new_value_by_qty = reval.added_value_by_qty = 0.0

    @api.depends('product_id.quantity_svl', 'product_id.value_svl', 'adjusted_layer_ids', 'lot_ids')
    def _compute_current_value_svl(self):
        for reval in self:
            if reval.adjusted_layer_ids:
                reval.current_quantity_svl = sum(reval.adjusted_layer_ids.mapped('remaining_qty'))
                reval.current_value_svl = sum(reval.adjusted_layer_ids.mapped('remaining_value'))
            elif self.env.context.get('active_model') == 'stock.lot' and reval.lot_ids:
                reval.current_quantity_svl = reval.lot_ids.quantity_svl
                reval.current_value_svl = reval.lot_ids.value_svl
            else:
                reval.current_quantity_svl = reval.product_id.quantity_svl
                reval.current_value_svl = reval.product_id.value_svl

    def action_validate_revaluation(self):
        """ Adjust the valuation of layers `self.adjusted_layer_ids` for
        `self.product_id` in `self.company_id`, or the entire stock for that
        product if no layers are specified (all layers with positive remaining
        quantity).

        - Change the standard price with the new valuation by product unit.
        - Create a manual stock valuation layer with the `added_value` of `self`.
        - Distribute the `added_value` on the remaining_value of the layers
        - If the Inventory Valuation of the product category is automated, create
        related account move.
        """
        self.ensure_one()
        if self.currency_id.is_zero(self.added_value):
            raise UserError(_("The added value doesn't have any impact on the stock valuation"))

        product_id = self.product_id.with_company(self.company_id)
        lot_ids = self.lot_ids.with_company(self.company_id)

        remaining_domain = [
            ('product_id', '=', product_id.id),
            ('remaining_qty', '>', 0),
            ('company_id', '=', self.company_id.id),
        ]
        if lot_ids:
            remaining_domain.append(('lot_id', '=', lot_ids.ids))
        layers_with_qty = self.env['stock.valuation.layer'].search(remaining_domain)
        adjusted_layers = self.adjusted_layer_ids or layers_with_qty

        remaining_qty = sum(adjusted_layers.mapped('remaining_qty'))
        remaining_value = self.added_value
        remaining_value_unit_cost = self.currency_id.round(remaining_value / remaining_qty)

        # adjust all layers by the unit value change per unit, except the last layer which gets
        # whatever is left. This avoids rounding issues e.g. $10 on 3 products => 3.33, 3.33, 3.34
        adjusted_value_by_lot = defaultdict(lambda: [0, 0])
        for svl in adjusted_layers:
            if self.product_id.uom_id.is_zero(svl.remaining_qty - remaining_qty):
                taken_remaining_value = remaining_value
            else:
                taken_remaining_value = remaining_value_unit_cost * svl.remaining_qty
            if self.product_id.uom_id.compare(svl.remaining_value + taken_remaining_value, 0) < 0:
                raise UserError(_('The value of a stock valuation layer cannot be negative. Landed cost could be use to correct a specific transfer.'))

            adjusted_value_by_lot[svl.lot_id][0] += taken_remaining_value
            adjusted_value_by_lot[svl.lot_id][1] += svl.remaining_qty
            svl.remaining_value += taken_remaining_value
            remaining_value -= taken_remaining_value
            remaining_qty -= svl.remaining_qty

        previous_value_svl = self.current_value_svl

        revaluation_svl_vals = []

        previous_cost = product_id.standard_price
        product_id.with_context(disable_auto_svl=True).standard_price += self.added_value / product_id.quantity_svl
        new_cost = product_id.standard_price

        description_base = _("Manual Stock Valuation: %s.", self.reason or _("No Reason Given"))

        for lot_id, (value, quantity) in adjusted_value_by_lot.items():
            cost_method = product_id.cost_method
            if cost_method not in ['average', 'fifo']:
                continue
            if not lot_id:
                description = _(
                    "%(description_base)s Product cost updated from %(previous)s to %(new_cost)s.",
                    description_base=description_base,
                    previous=previous_cost,
                    new_cost=new_cost,
                )
                revaluation_svl_vals.append({
                    'company_id': self.company_id.id,
                    'product_id': product_id.id,
                    'description': description,
                    'value': self.added_value,
                    'quantity': 0,
                })
            else:
                lot_id.with_context(disable_auto_svl=True).standard_price += value / lot_id.quantity_svl
                description = _(
                    "%(description_base)s lot/serial number cost updated from %(previous)s to %(new_cost)s.",
                    description_base=description_base,
                    previous=previous_cost,
                    new_cost=lot_id.standard_price,
                )
                revaluation_svl_vals.append({
                    'company_id': self.company_id.id,
                    'product_id': product_id.id,
                    'description': description,
                    'value': value,
                    'lot_id': lot_id.id,
                    'quantity': 0,
                })

        revaluation_svl = self.env['stock.valuation.layer'].create(revaluation_svl_vals)

        # If the Inventory Valuation of the product category is automated, create related account move.
        if self.property_valuation != 'real_time':
            return True

        accounts = product_id.product_tmpl_id.get_product_accounts()

        if self.added_value < 0:
            debit_account_id = self.account_id.id
            credit_account_id = accounts.get('stock_valuation') and accounts['stock_valuation'].id
        else:
            debit_account_id = accounts.get('stock_valuation') and accounts['stock_valuation'].id
            credit_account_id = self.account_id.id

        move_description = _('%(user)s changed stock valuation from  %(previous)s to %(new_value)s - %(product)s\n%(reason)s',
            user=self.env.user.name,
            previous=previous_value_svl,
            new_value=previous_value_svl + self.added_value,
            product=product_id.display_name,
            reason=description,
        )

        if self.adjusted_layer_ids:
            adjusted_layer_descriptions = [f"{layer.reference} (id: {layer.id})" for layer in self.adjusted_layer_ids]
            move_description += _("\nAffected valuation layers: %s", adjusted_layer_descriptions)

        move_vals = [{
            'journal_id': self.account_journal_id.id or accounts['stock_journal'].id,
            'company_id': self.company_id.id,
            'ref': _("Revaluation of %s", product_id.display_name),
            'stock_valuation_layer_ids': [(6, None, [svl.id])],
            'date': self.date or fields.Date.today(),
            'move_type': 'entry',
            'line_ids': [(0, 0, {
                'name': move_description,
                'account_id': debit_account_id,
                'debit': abs(svl.value),
                'credit': 0,
                'product_id': svl.product_id.id,
            }), (0, 0, {
                'name': move_description,
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(svl.value),
                'product_id': svl.product_id.id,
            })],
        } for svl in revaluation_svl]
        account_move = self.env['account.move'].create(move_vals)
        account_move._post()

        return True
