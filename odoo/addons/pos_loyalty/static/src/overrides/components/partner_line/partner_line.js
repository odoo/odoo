/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { patch } from "@web/core/utils/patch";
import { formatFloat } from "@web/core/utils/numbers";

patch(PartnerLine.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },
    _getLoyaltyPointsRepr(loyaltyCard) {
        const program = this.pos.program_by_id[loyaltyCard.program_id];
        if (program.program_type === "ewallet") {
            return `${program.name}: ${this.env.utils.formatCurrency(loyaltyCard.balance)}`;
        }
        const balanceRepr = formatFloat(loyaltyCard.balance, { digits: [69, 2] });
        if (program.portal_visible) {
            return `${balanceRepr} ${program.portal_point_name}`;
        }
        return _t("%s Points", balanceRepr);
    },
});
