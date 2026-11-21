import { LoyaltyRule } from "@pos_loyalty/app/models/loyalty_rule";
import { patch } from "@web/core/utils/patch";

patch(LoyaltyRule.prototype, {
    /**
     * Split payment lines only move an amount between the origin order and the split
     * payment orders. They are not goods, so they never count as units.
     * mirror of *models/loyalty_rule.py* LoyaltyRule._qualifying_lines
     * @override
     */
    _qualifyingLines(order) {
        const lines = super._qualifyingLines(order);
        if (this.reward_point_mode !== "unit") {
            return lines;
        }
        return lines.filter((line) => !line.isSplitPaymentLine);
    },
});
