/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { useSubEnv } from '@odoo/owl';
import {
    ProductConfiguratorDialog
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';

patch(ProductConfiguratorDialog.prototype, {
    setup() {
        super.setup(...arguments);

        useSubEnv({
            isQuantityAllowed: this._isQuantityAllowed.bind(this),
        });
    },

    async _setQuantity(productTmplId, quantity) {
        const product = this._findProduct(productTmplId);
        if (!this._isQuantityAllowed(product, quantity)) {
            quantity = product.max_quantity;
        }
        return super._setQuantity(productTmplId, quantity);
    },

    /**
     * Check whether the provided product quantity can be added to the cart.
     *
     * @param {Object} product - The provided product.
     * @param {Number} quantity - The new quantity of the product.
     * @return {Boolean} - Whether the provided product quantity can be added to the cart.
     */
    _isQuantityAllowed(product, quantity) {
        return !('max_quantity' in product) || product.max_quantity >= quantity;
    },

    /**
     * Check whether all selected product quantities can be added to the cart.
     *
     * @return {Boolean} - Whether all selected product quantities can be added to the cart.
     */
    areQuantitiesAllowed() {
        return this.state.products.every(p => this._isQuantityAllowed(p, p.quantity));
    },
});
