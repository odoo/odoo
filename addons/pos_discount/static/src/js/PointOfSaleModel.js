odoo.define('pos_discount.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const { patch } = require('web.utils');

    patch(PointOfSaleModel.prototype, 'pos_discount', {
        async actionApplyDiscount(order, pc) {
            const product = this.getRecord('product.product', this.config.discount_product_id);
            if (!product) {
                await this.env.ui.askUser('ErrorPopup', {
                    title: this.env._t('No discount product found'),
                    body: this.env._t(
                        "The discount product seems misconfigured. Make sure it is flagged as 'Can be Sold' and 'Available in Point of Sale'."
                    ),
                });
                return;
            }

            // Remove existing discounts
            for (const line of this.getOrderlines(order)) {
                if (line.product_id === product.id) {
                    this._deleteOrderline(order, line);
                }
            }

            // Add discount
            // We add the price as manually set to avoid recomputation when changing customer.
            const { noTaxWithDiscount, withTaxWithDiscount } = this.getOrderTotals(order);
            let base_to_discount = noTaxWithDiscount;
            if (product.taxes_id.length) {
                const first_tax = this.getRecord('account.tax', product.taxes_id[0]);
                if (first_tax.price_include) {
                    base_to_discount = withTaxWithDiscount;
                }
            }
            const discount = (-pc / 100.0) * base_to_discount;

            if (discount < 0) {
                this.actionAddProduct(order, product, {
                    price_unit: discount,
                    price_manually_set: true,
                });
            }
        },
    });

    return PointOfSaleModel;
});
