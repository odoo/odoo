/** @odoo-module */

import "@pos_loyalty/app/models/pos_order";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    /**
     * For Peru, eWallet/gift card balances are tax-included amounts (SUNAT retail convention).
     * Keep the tax-included price on the reward line instead of converting to tax-excluded,
     * which causes a 0.01 rounding drift with IGV.
     */
    _getRewardLineValuesDiscount(args) {
        const reward = args.reward;
        if (
            this.company.country_id?.code !== "PE" ||
            !["ewallet", "gift_card"].includes(reward.program_id.program_type)
        ) {
            return super._getRewardLineValuesDiscount(...arguments);
        }

        const rewardLines = super._getRewardLineValuesDiscount(...arguments);
        if (!Array.isArray(rewardLines) || !rewardLines.length) {
            return rewardLines;
        }

        rewardLines[0].price_unit = -rewardLines[0].points_cost;
        return rewardLines;
    },
});
