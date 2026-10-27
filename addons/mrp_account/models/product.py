# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import float_round, groupby, topological_sort


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()
        if self.categ_id:
            # If category set on the product take production account from category even if
            # production account on category is False
            production_account = self.categ_id.property_stock_account_production_cost_id
        else:
            ProductCategory = self.env['product.category']
            production_account = (
                self.valuation == 'real_time'
                and ProductCategory._fields['property_stock_account_production_cost_id'].get_company_dependent_fallback(
                    ProductCategory
                )
                or self.env['account.account']
            )
        accounts['production'] = production_account
        return accounts

    def action_bom_cost(self):
        templates = self.filtered(lambda t: t.product_variant_count == 1 and t.bom_count > 0)
        if templates:
            return templates.mapped('product_variant_id').action_bom_cost()

    def button_bom_cost(self):
        templates = self.filtered(lambda t: t.product_variant_count == 1 and t.bom_count > 0)
        if templates:
            return templates.mapped('product_variant_id').button_bom_cost()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def button_bom_cost(self):
        self.ensure_one()
        self._set_price_from_bom()

    def action_bom_cost(self):
        self._set_price_from_bom()

    def _set_price_from_bom(self):
        """ Set the cost of the products from their BoM, or from the BoM producing them as a
        by-product. Products of ``self`` that are components of other products of ``self`` are
        computed first, and their new cost is used for the products containing them.
        """
        Bom = self.env['mrp.bom']
        bom_by_product = Bom._bom_find(self)

        # For Products without BoMs, Find the BoM producing them as by-products
        byproduct_bom_by_product = {}
        products_without_bom = self.filtered(lambda p: not bom_by_product.get(p))
        if products_without_bom:
            boms = Bom.search([('byproduct_ids.product_id', 'in', products_without_bom.ids)], order='sequence, product_id, id')
            for bom in boms:
                for product in bom.byproduct_ids.product_id & products_without_bom:
                    byproduct_bom_by_product.setdefault(product, bom)
        bom_by_product = {**byproduct_bom_by_product, **bom_by_product}

        if not bom_by_product:
            return

        # Fetch everything needed to compute the prices at once, whatever the prefetch sets
        boms = Bom.union(bom_by_product.values())
        boms.fetch(['type', 'product_qty', 'uom_id', 'extra_cost', 'bom_line_ids', 'byproduct_ids', 'operation_ids'])
        boms.bom_line_ids.fetch(['product_id', 'product_qty', 'uom_id', 'bom_product_template_attribute_value_ids'])
        boms.bom_line_ids.product_id.fetch(['standard_price', 'uom_id'])

        # Sort the products so that components prices are computed before the products using them
        sorted_products = topological_sort({
            product: bom.bom_line_ids.product_id
            for product, bom in bom_by_product.items()
        })

        # Filled while iterating, read by _get_bom_components_price for the components of self
        price_by_product_id = {}
        for product in sorted_products:
            product = product.with_context(bom_price_by_product_id=price_by_product_id, action_button_product=product)
            bom = bom_by_product[product]
            if product not in byproduct_bom_by_product:
                price_by_product_id[product.id] = product._compute_bom_price(bom)
            elif price := product._compute_bom_price(bom, byproduct_bom=True):
                price_by_product_id[product.id] = price

        price_by_product = {
            product: price_by_product_id[product.id]
            for product in self
            if product.id in price_by_product_id and price_by_product_id[product.id] != product.standard_price
        }
        if not price_by_product:
            return
        # One write per distinct price, and a single revaluation for all the products
        old_price = {product: product.standard_price for product in price_by_product}
        for price, products in groupby(price_by_product, key=price_by_product.get):
            self.env['product.product'].concat(products).with_context(disable_auto_revaluation=True).standard_price = price
        if not self.env.context.get('disable_auto_revaluation'):
            self.env['product.product'].concat(price_by_product)._change_standard_price(old_price)

    def _get_bom_components_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        """
        Calculates only the price of the BoM components
        """
        self.ensure_one()
        if not bom:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []
        total = bom.extra_cost if bom.type == 'normal' else 0
        for opt in bom.operation_ids:
            if opt._skip_operation_line(self):
                continue

            total += opt.cost

        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(line.child_bom_id, boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.uom_id) * line.product_qty
            else:
                # use the new cost of the components recomputed in the same batch (see _set_price_from_bom)
                price = self.env.context.get('bom_price_by_product_id', {}).get(line.product_id.id, line.product_id.standard_price)
                total += line.product_id.uom_id._compute_price(price, line.uom_id) * line.product_qty
        if byproduct_bom:
            byproduct_lines = bom.byproduct_ids.filtered(lambda b: b.product_id == self and b.cost_share != 0)
            product_uom_qty = 0
            for line in byproduct_lines:
                product_uom_qty += line.uom_id._compute_quantity(line.product_qty, self.uom_id, round=False)
            byproduct_cost_share = sum(byproduct_lines.mapped('cost_share'))
            if byproduct_cost_share and product_uom_qty:
                return total * byproduct_cost_share / 100 / product_uom_qty
        else:
            byproduct_cost_share = sum(bom.byproduct_ids.mapped('cost_share'))
            if byproduct_cost_share:
                total *= float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001)
            return bom.uom_id._compute_price(total / bom.product_qty, self.uom_id)
        return 0.0

    def _compute_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        return self._get_bom_components_price(bom, boms_to_recompute=boms_to_recompute, byproduct_bom=byproduct_bom)

    def _compute_value(self):
        """
        Exclude kit products from inventory valuation to avoid double counting.
        Only non-kit products are valuated; kits are set to zero value.
        """
        non_kit_products, kit_products = self.partitioned(lambda product: not product.is_kits)
        super(ProductProduct, non_kit_products)._compute_value()
        for kit_product in kit_products:
            kit_product.company_currency_id = kit_product.company_id.currency_id or self.env.company.currency_id
            kit_product.total_value = 0.0
            kit_product.avg_cost = 0.0

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        super()._update_standard_price(extra_value=extra_value, extra_quantity=extra_quantity)
        # Kits are never moved themselves: recompute the cost of the AVCO kits using these products,
        # including the kits containing those kits (_set_price_from_bom handles the order).
        kits = self.env['product.product'].sudo()
        products = self
        while products:
            boms = self.env['mrp.bom'].sudo().search([
                ('type', '=', 'phantom'),
                ('bom_line_ids.product_id', 'in', products.ids),
                ('company_id', 'in', [False, self.env.company.id]),
                ('active', '=', True),
            ])
            products = boms.product_id | boms.filtered(lambda b: not b.product_id).product_tmpl_id.product_variant_ids
            # a non AVCO kit keeps its cost, so it cannot change the cost of the kits containing it
            products = products.filtered(lambda p: p.cost_method == 'average') - kits
            kits |= products
        # kits are not valued (see _compute_value), a revaluation would be pointless
        kits.with_context(disable_auto_revaluation=True)._set_price_from_bom()

class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_account_production_cost_id = fields.Many2one(
        'account.account', 'Production Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""This account will be used as a valuation counterpart for both components and final products for manufacturing orders.
                If there are any workcenter/employee costs, this value will remain on the account once the production is completed.""")
