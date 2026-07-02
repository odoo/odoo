// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    onNumpadClick(buttonValue) {
        if (
            this.pos.isPhilippinesCompany() &&
            ["quantity", "discount", "price"].includes(buttonValue)
        ) {
            void this.pos.l10nPhFlushPendingDecrease();
        }
        return super.onNumpadClick(...arguments);
    },
});
