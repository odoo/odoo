// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { LoyaltyReward } from "@pos_loyalty/app/models/loyalty_reward";
import { patch } from "@web/core/utils/patch";

patch(LoyaltyReward.prototype, {
    /**
     * SC/PWD privileges can't be combined with any other discount (RA 9994,
     * RA 10754): discount rewards only ever apply on the lines that aren't
     * privileged. They are hidden from the selection itself, rather than
     * filtered out of its result, so that e.g. a discount on the cheapest
     * product goes to the cheapest regular one.
     */
    getDiscountApplicableLines(order) {
        const regularOrder = Object.create(order, {
            getOrderlines: {
                value: () =>
                    order.getOrderlines().filter((line) => !line.l10n_ph_discount_privilege_id),
            },
        });
        return super.getDiscountApplicableLines(regularOrder);
    },
});
