# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class StockValuationLayerRevaluation(models.TransientModel):
    _name = 'stock.valuation.layer.revaluation'
    _description = "Wizard model to reavaluate a stock inventory for a product"
    _check_company_auto = True

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        if res.get('product_id'):
            product = self.env['product.product'].browse(res['product_id'])
            if product.categ_id.property_cost_method == 'standard':
                raise UserError(_("You cannot revalue a product with a standard cost method."))
            if product.quantity_svl <= 0:
                raise UserError(_("You cannot revalue a product with an empty or negative stock."))
            if 'account_journal_id' not in res and 'account_journal_id' in default_fields and product.categ_id.property_valuation == 'real_time':
                accounts = product.product_tmpl_id.get_product_accounts()
                res['account_journal_id'] = accounts['stock_journal'].id
        return res

    company_id = fields.Many2one('res.company', "Company", readonly=True, required=True)
    currency_id = fields.Many2one('res.currency', "Currency", related='company_id.currency_id', required=True)

    product_id = fields.Many2one('product.product', "Related product", required=True, check_company=True)
    property_valuation = fields.Selection(related='product_id.categ_id.property_valuation')
    product_uom_name = fields.Char("Unit of Measure", related='product_id.uom_id.name')
    current_value_svl = fields.Float("Current Value", related="product_id.value_svl")
    current_quantity_svl = fields.Float("Current Quantity", related="product_id.quantity_svl")

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

    def action_validate_revaluation(self):
        """ Revaluate the stock for `self.product_id` in `self.company_id`.

        - Change the stardard price with the new valuation by product unit.
        - Create a manual stock valuation layer with the `added_value` of `self`.
        - Distribute the `added_value` on the remaining_value of layers still in stock (with a remaining quantity)
        - If the Inventory Valuation of the product category is automated, create
        related account move.
        """
        self.ensure_one()
        if self.currency_id.is_zero(self.added_value):
            raise UserError(_("The added value doesn't have any impact on the stock valuation"))

        product_id = self.product_id.with_company(self.company_id)

        remaining_svls = self.env['stock.valuation.layer'].search([
            ('product_id', '=', product_id.id),
            ('remaining_qty', '>', 0),
            ('company_id', '=', self.company_id.id),
        ])

        # Create a manual stock valuation layer
        if self.reason:
            description = _("Manual Stock Valuation: %s.", self.reason)
        else:
            description = _("Manual Stock Valuation: No Reason Given.")
        if product_id.categ_id.property_cost_method == 'average':
            description += _(
                " Product cost updated from %(previous)s to %(new_cost)s.",
                previous=product_id.standard_price,
                new_cost=product_id.standard_price + self.added_value / self.current_quantity_svl
            )
        revaluation_svl_vals = {
            'company_id': self.company_id.id,
            'product_id': product_id.id,
            'description': description,
            'value': self.added_value,
            'quantity': 0,
        }

        remaining_qty = sum(remaining_svls.mapped('remaining_qty'))
        remaining_value = self.added_value
        remaining_value_unit_cost = self.currency_id.round(remaining_value / remaining_qty)
        for svl in remaining_svls:
            if float_is_zero(svl.remaining_qty - remaining_qty, precision_rounding=self.product_id.uom_id.rounding):
                taken_remaining_value = remaining_value
            else:
                taken_remaining_value = remaining_value_unit_cost * svl.remaining_qty
            if float_compare(svl.remaining_value + taken_remaining_value, 0, precision_rounding=self.product_id.uom_id.rounding) < 0:
                raise UserError(_('The value of a stock valuation layer cannot be negative. Landed cost could be use to correct a specific transfer.'))

            svl.remaining_value += taken_remaining_value
            remaining_value -= taken_remaining_value
            remaining_qty -= svl.remaining_qty

        revaluation_svl = self.env['stock.valuation.layer'].create(revaluation_svl_vals)

        # Update the stardard price in case of AVCO
        if product_id.categ_id.property_cost_method in ('average', 'fifo'):
            product_id.with_context(disable_auto_svl=True).standard_price += self.added_value / self.current_quantity_svl

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

        move_vals = {
            'journal_id': self.account_journal_id.id or accounts['stock_journal'].id,
            'company_id': self.company_id.id,
            'ref': _("Revaluation of %s", product_id.display_name),
            'stock_valuation_layer_ids': [(6, None, [revaluation_svl.id])],
            'date': self.date or fields.Date.today(),
            'move_type': 'entry',
            'line_ids': [(0, 0, {
                'name': _('%(user)s changed stock valuation from  %(previous)s to %(new_value)s - %(product)s',
                    user=self.env.user.name,
                    previous=self.current_value_svl,
                    new_value=self.current_value_svl + self.added_value,
                    product=product_id.display_name,
                ),
                'account_id': debit_account_id,
                'debit': abs(self.added_value),
                'credit': 0,
                'product_id': product_id.id,
            }), (0, 0, {
                'name': _('%(user)s changed stock valuation from  %(previous)s to %(new_value)s - %(product)s',
                    user=self.env.user.name,
                    previous=self.current_value_svl,
                    new_value=self.current_value_svl + self.added_value,
                    product=product_id.display_name,
                ),
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(self.added_value),
                'product_id': product_id.id,
            })],
        }
        account_move = self.env['account.move'].create(move_vals)
        account_move._post()

        return True
