import { LoyaltyRule } from "@pos_loyalty/app/models/loyalty_rule";
import { patch } from "@web/core/utils/patch";

patch(LoyaltyRule.prototype, {
    _countsForPoints(line) {
        return !line.product_id.product_tmpl_id.is_deposit && super._countsForPoints(line);
    },
});
