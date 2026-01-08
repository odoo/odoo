/** @odoo-module */

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    isSelfOrderAvailable(product_id) {
        return this.pos.db.product_by_id[product_id].self_order_available;
    },
});
