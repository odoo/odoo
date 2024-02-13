/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { Product } from '@sale/js/product/product';

patch(Product, {
    props: {
        ...Product.props,
        is_storable: { type: Boolean, optional: true },
        allow_out_of_stock_order: { type: Boolean, optional: true },
        free_qty: { type: Number, optional: true },
    },
});

patch(Product.prototype, {
    /**
     * Check whether this product is out of stock.
     *
     * @return {Boolean} - Whether this product is out of stock.
     */
    isOutOfStock() {
        return !this.env.isQuantityAllowed(this.props, 1);
    },
});
