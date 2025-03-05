import { patch } from '@web/core/utils/patch';
import { ProductProduct } from '@sale/js/models/product_product';

patch(ProductProduct.prototype, {
    /**
     * @param {number} max_quantity
     * @param args Super's parameter list.
     */
    setup({max_quantity, ...args}) {
        super.setup(args);
        this.max_quantity = max_quantity;
    },

    /**
     * Check whether the provided quantity can be added to the cart.
     *
     * @param {Number} quantity The quantity to check.
     * @return {Boolean} Whether the product quantity can be added to the cart.
     */
    isQuantityAllowed(quantity) {
        return this.max_quantity === undefined || this.max_quantity >= quantity;
    },
});
