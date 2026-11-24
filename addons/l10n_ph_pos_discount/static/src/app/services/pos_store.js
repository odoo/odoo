// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

// Orders pos_discount is applying its global discount on, with the number of
// applications in progress for each of them.
const ordersApplyingGlobalDiscount = new Map();

patch(PosStore.prototype, {
    async applyDiscount(value, type, order = this.getOrder()) {
        // Until it is fully applied, whatever pos_discount awaits before
        // picking the discountable lines.
        ordersApplyingGlobalDiscount.set(order, (ordersApplyingGlobalDiscount.get(order) || 0) + 1);
        try {
            return await super.applyDiscount(...arguments);
        } finally {
            const count = ordersApplyingGlobalDiscount.get(order) - 1;
            if (count) {
                ordersApplyingGlobalDiscount.set(order, count);
            } else {
                ordersApplyingGlobalDiscount.delete(order);
            }
        }
    },
});

patch(PosOrderline.prototype, {
    /**
     * SC/PWD privileges can't be combined with any other discount (RA 9994,
     * RA 10754): a privileged share is discounted by its privilege only.
     *
     * Only while applying the global discount on its order: pos_restaurant,
     * when installed, also uses this hook to count the items a bill can be
     * split into, privileged ones included.
     */
    isGlobalDiscountApplicable() {
        if (this.l10n_ph_discount_privilege_id && ordersApplyingGlobalDiscount.has(this.order_id)) {
            return false;
        }
        return super.isGlobalDiscountApplicable(...arguments);
    },
});
