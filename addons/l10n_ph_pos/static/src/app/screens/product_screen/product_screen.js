// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { L10N_PH_PRIVILEGED_LOCKED_MODES } from "@l10n_ph_pos/app/services/pos_store";

patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const buttons = super.getNumpadButtons();
        if (!this.currentOrder?.getSelectedOrderline()?.l10n_ph_discount_privilege_id) {
            return buttons;
        }
        // A privileged share's quantity, discount and price are set by the
        // split (see OrderSummary.updateSelectedOrderline).
        return buttons.map((button) =>
            L10N_PH_PRIVILEGED_LOCKED_MODES.includes(button.value)
                ? { ...button, disabled: true }
                : button
        );
    },
});
