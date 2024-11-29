import { patch } from '@web/core/utils/patch';
import { ProductProduct } from '@sale/js/models/product_product';

patch(ProductProduct.prototype, {
    /**
     * @param {number} free_qty
     * @param args Super's parameter list.
     */
    setup({free_qty, ...args}) {
        super.setup(args);
        this.free_qty = free_qty;
    },

    /**
     * Check whether the provided quantity can be added to the cart.
     *
     * @param {Number} quantity The quantity to check.
     * @return {Boolean} Whether the product quantity can be added to the cart.
     */
    isQuantityAllowed(quantity) {
        return this.free_qty === undefined || this.free_qty >= quantity;
    },
});
