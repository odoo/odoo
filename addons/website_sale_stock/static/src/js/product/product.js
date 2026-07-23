import { patch } from '@web/core/utils/patch';
import { t } from "@odoo/owl";
import { Product, productProps } from '@sale/js/product/product';

Object.assign(productProps, {
    free_qty: t.number().optional(),
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
