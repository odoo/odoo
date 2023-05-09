/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { PartnerLine } from "@point_of_sale/js/Screens/PartnerListScreen/PartnerLine";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";
import { formatFloat } from "@web/views/fields/formatters";

patch(PartnerLine.prototype, "pos_loyalty.PartnerLine", {
    setup() {
        this._super(...arguments);
        this.pos = usePos();
    },
    _getLoyaltyPointsRepr(loyaltyCard) {
        const program = this.pos.globalState.program_by_id[loyaltyCard.program_id];
        if (program.program_type === "ewallet") {
            return `${program.name}: ${this.env.utils.formatCurrency(loyaltyCard.balance)}`;
        }
        const balanceRepr = formatFloat(loyaltyCard.balance, { digits: [69, 2] });
        if (program.portal_visible) {
            return `${balanceRepr} ${program.portal_point_name}`;
        }
        return sprintf(this.env._t("%s Points"), balanceRepr);
    },
});
