import { LoyaltyRule } from "@pos_loyalty/app/models/loyalty_rule";
import { patch } from "@web/core/utils/patch";

patch(LoyaltyRule.prototype, {
    _qualifyingLines(order) {
        const lines = super._qualifyingLines(order);
        if (this.reward_point_mode !== "unit") {
            return lines;
        }
        return lines.filter((line) => !line.isSplitPaymentLine);
    },
});
