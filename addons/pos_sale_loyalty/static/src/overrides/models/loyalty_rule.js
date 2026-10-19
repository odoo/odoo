import { LoyaltyRule } from "@pos_loyalty/app/models/loyalty_rule";
import { patch } from "@web/core/utils/patch";

patch(LoyaltyRule.prototype, {
    _countsForPoints(line) {
        return !line.sale_order_origin_id && super._countsForPoints(line);
    },
});
