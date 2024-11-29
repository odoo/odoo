import { patch } from '@web/core/utils/patch';
import {
    ComboConfiguratorDialog
} from '@sale/js/combo_configurator_dialog/combo_configurator_dialog';

patch(ComboConfiguratorDialog.prototype, {
    async selectComboItem(comboId, comboItem) {
        if (!comboItem.product.isQuantityAllowed(this.state.quantity)) {
            return;
        }
        super.selectComboItem(...arguments);
    },

    /**
     * Check whether the provided combo quantity can be added to the cart.
     *
     * @param {Number} quantity The quantity to check.
     * @return {Boolean} Whether the combo quantity can be added to the cart.
     */
    isComboQuantityAllowed(quantity) {
        return this._selectedComboItems.every(
            comboItem => comboItem.product.isQuantityAllowed(quantity)
        );
    },
});
