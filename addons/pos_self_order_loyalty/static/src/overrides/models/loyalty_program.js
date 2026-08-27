import { patch } from "@web/core/utils/patch";
import { LoyaltyProgram } from "@pos_loyalty/app/models/loyalty_program";

patch(LoyaltyProgram.prototype, {
    getDisplayPoints(order) {
        const points = Math.round(this.getPoints(order) * 100) / 100;
        return `${points} ${this.portal_point_name}`;
    },
});
