// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    onNumpadClick(buttonValue) {
        // `super.onNumpadClick` calls the number buffer's `capture()` for mode-switch
        // buttons, which synchronously applies any debounced pending digit (and updates
        // `_l10nPhPending` through `updateSelectedOrderline`). Flush must happen after
        // that, otherwise it runs against stale state and silently misses the decrease.
        const result = super.onNumpadClick(...arguments);
        if (
            this.pos.isPhilippinesCompany() &&
            ["quantity", "discount", "price"].includes(buttonValue)
        ) {
            void this.pos.l10nPhFlushPendingDecrease();
        }
        return result;
    },
});
