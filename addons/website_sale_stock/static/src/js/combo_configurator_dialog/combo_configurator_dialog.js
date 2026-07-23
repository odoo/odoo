import { patch } from '@web/core/utils/patch';
import {
    ComboConfiguratorDialog
} from '@sale/js/combo_configurator_dialog/combo_configurator_dialog';

patch(ComboConfiguratorDialog.prototype, {
    async selectComboItem(combo, comboItem) {
        if (!comboItem.product.isQuantityAllowed(this.state.quantity)) {
            return;
        }
        super.selectComboItem(...arguments);
    },

    async setQuantity(quantity) {
        if (!this.isComboQuantityAllowed(quantity)) {
            quantity = Math.min(
                ...this._selectedComboItems
                    .map(comboItem => comboItem.product.free_qty !== undefined
                        ? Math.floor(comboItem.product.free_qty / comboItem.selected_qty)
                        : undefined)
                    .filter(maxQty => maxQty !== undefined)
            );
        }
        return super.setQuantity(quantity);
    },

    async setItemQuantity(comboId, comboItem, quantity, configuredItem = null) {
        const freeQty = comboItem.product.free_qty;

        if (quantity > 0 && freeQty !== undefined) {
            quantity = Math.min(quantity, freeQty);
        }

        return super.setItemQuantity(comboId, comboItem, quantity, configuredItem);
    },

    /**
     * Check whether the provided combo quantity can be added to the cart.
     *
     * @param {Number} quantity The quantity to check.
     * @return {Boolean} Whether the combo quantity can be added to the cart.
     */
    isComboQuantityAllowed(quantity) {
        return this._selectedComboItems.every(
            comboItem => comboItem.product.isQuantityAllowed(quantity * comboItem.selected_qty)
        );
    },
});
