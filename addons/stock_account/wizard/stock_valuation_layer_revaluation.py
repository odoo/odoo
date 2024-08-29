# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, format_list


class StockValuationLayerRevaluation(models.TransientModel):
    _description = "Wizard model to reavaluate a stock inventory for a product"
    _check_company_auto = True

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        context = self.env.context
        if context.get('active_model') == 'stock.valuation.layer':
            # coming from action button "Adjust Valuation" in valuation layer list view
            active_ids = context.get('active_ids')
            layers = self.env['stock.valuation.layer'].browse(active_ids).exists()
            product = layers.product_id
            if len(product) > 1:
                raise UserError(_("You cannot revalue multiple products at once"))
            if any(float_is_zero(layer.remaining_qty, precision_rounding=product.uom_id.rounding) for layer in layers):
                raise UserError(_("You cannot adjust the valuation of a layer with zero quantity"))
            res['adjusted_layer_ids'] = active_ids
            res['product_id'] = product.id
        product = self.env['product.product'].browse(res.get('product_id'))
        if 'product_id' in default_fields:
            if not product:
                raise UserError(_("You cannot adjust valuation without a product"))
            if product.categ_id.property_cost_method == 'standard':
                raise UserError(_("You cannot revalue a product with a standard cost method."))
            if product.quantity_svl <= 0:
                raise UserError(_("You cannot revalue a product with an empty or negative stock."))
            if 'account_journal_id' not in res and 'account_journal_id' in default_fields and product.categ_id.property_valuation == 'real_time':
                accounts = product.product_tmpl_id.get_product_accounts()
                res['account_journal_id'] = accounts['stock_journal'].id
        return res

    company_id = fields.Many2one('res.company', "Company", readonly=True, required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', "Currency", related='company_id.currency_id', required=True)

    adjusted_layer_ids = fields.Many2many('stock.valuation.layer', string="Valuation Layers", help="Valuations layers being adjusted")
    product_id = fields.Many2one('product.product', "Related product", required=True, check_company=True)
    property_valuation = fields.Selection(related='product_id.categ_id.property_valuation')
    product_uom_name = fields.Char("Unit of Measure", related='product_id.uom_id.name')
    current_value_svl = fields.Float("Current Value", compute='_compute_current_value_svl')
    current_quantity_svl = fields.Float("Current Quantity", compute='_compute_current_value_svl')

    added_value = fields.Monetary("Added value", required=True)
    new_value = fields.Monetary("New value", compute='_compute_new_value')
    new_value_by_qty = fields.Monetary("New value by quantity", compute='_compute_new_value')
    reason = fields.Char("Reason", help="Reason of the revaluation")

    account_journal_id = fields.Many2one('account.journal', "Journal", check_company=True)
    account_id = fields.Many2one('account.account', "Counterpart Account", domain=[('deprecated', '=', False)], check_company=True)
    date = fields.Date("Accounting Date")

    @api.depends('current_value_svl', 'current_quantity_svl', 'added_value')
    def _compute_new_value(self):
        for reval in self:
            reval.new_value = reval.current_value_svl + reval.added_value
            if not float_is_zero(reval.current_quantity_svl, precision_rounding=self.product_id.uom_id.rounding):
                reval.new_value_by_qty = reval.new_value / reval.current_quantity_svl
            else:
                reval.new_value_by_qty = 0.0

    @api.depends('product_id.quantity_svl', 'product_id.value_svl', 'adjusted_layer_ids')
    def _compute_current_value_svl(self):
        for reval in self:
            if not reval.adjusted_layer_ids:
                reval.current_quantity_svl = reval.product_id.quantity_svl
                reval.current_value_svl = reval.product_id.value_svl
            else:
                reval.current_quantity_svl = sum(reval.adjusted_layer_ids.mapped('remaining_qty'))
                reval.current_value_svl = sum(reval.adjusted_layer_ids.mapped('remaining_value'))

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
        layers_with_qty = self.env['stock.valuation.layer'].search([
            ('product_id', '=', product_id.id),
            ('remaining_qty', '>', 0),
            ('company_id', '=', self.company_id.id),
        ])
        adjusted_layers = self.adjusted_layer_ids or layers_with_qty
        qty_to_adjust = sum(adjusted_layers.mapped('remaining_qty'))
        value_change_to_apply = self.added_value
        unit_value_change = self.currency_id.round(self.added_value / qty_to_adjust)
        # adjust all layers by the unit value change per unit, except the last layer which gets
        # whatever is left. This avoids rounding issues e.g. $10 on 3 products => 3.33, 3.33, 3.34
        for layer in adjusted_layers:
            if layer != adjusted_layers[-1]:
                value_change = unit_value_change * layer.remaining_qty
                layer.remaining_value += value_change
                value_change_to_apply -= value_change
            else:
                layer.remaining_value += value_change_to_apply

            if float_compare(layer.remaining_value, 0, precision_rounding=self.product_id.uom_id.rounding) < 0:
                raise UserError(_('The value of a stock valuation layer cannot be negative. Landed cost could be used to correct a specific transfer.'))

        description = _("Manual Stock Valuation: %s.", self.reason or _("No Reason Given"))
        # Update the stardard price in case of AVCO/FIFO
        cost_method = product_id.categ_id.property_cost_method
        if cost_method in ['average', 'fifo']:
            previous_cost = product_id.standard_price
            total_product_qty = sum(layers_with_qty.mapped('remaining_qty'))
            product_id.with_context(disable_auto_svl=True).standard_price += self.added_value / total_product_qty
            description += _(
                " Product cost updated from %(previous)s to %(new_cost)s.",
                previous=previous_cost,
                new_cost=product_id.standard_price
            )

        previous_value_svl = self.current_value_svl
        revaluation_layer = self.env['stock.valuation.layer'].create({
            'company_id': self.company_id.id,
            'product_id': product_id.id,
            'description': description,
            'value': self.added_value,
            'quantity': 0,
        })

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
            move_description += _("\nAffected valuation layers: %s", format_list(self.env, adjusted_layer_descriptions))

        move_vals = {
            'journal_id': self.account_journal_id.id or accounts['stock_journal'].id,
            'company_id': self.company_id.id,
            'ref': _("Revaluation of %s", product_id.display_name),
            'stock_valuation_layer_ids': [(6, None, [revaluation_layer.id])],
            'date': self.date or fields.Date.today(),
            'move_type': 'entry',
            'line_ids': [(0, 0, {
                'name': move_description,
                'account_id': debit_account_id,
                'debit': abs(self.added_value),
                'credit': 0,
                'product_id': product_id.id,
            }), (0, 0, {
                'name': move_description,
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(self.added_value),
                'product_id': product_id.id,
            })],
        }
        account_move = self.env['account.move'].create(move_vals)
        account_move._post()

        return True
