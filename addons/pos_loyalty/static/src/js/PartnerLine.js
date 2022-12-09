/** @odoo-module */

import PartnerLine from "@point_of_sale/js/Screens/PartnerListScreen/PartnerLine";
import Registries from "@point_of_sale/js/Registries";

const PosLoyaltyPartnerLine = (PartnerLine) =>
    class extends PartnerLine {
        _getLoyaltyPointsRepr(loyaltyCard) {
            const program = this.env.pos.program_by_id[loyaltyCard.program_id];
            if (program.program_type === "ewallet") {
                return `${program.name}: ${this.env.pos.format_currency(loyaltyCard.balance)}`;
            }
            const balanceRepr = this.env.pos.format_pr(loyaltyCard.balance, 0.01);
            if (program.portal_visible) {
                return `${balanceRepr} ${program.portal_point_name}`;
            }
            return _.str.sprintf(this.env._t("%s Points"), balanceRepr);
        }
    };

Registries.Component.extend(PartnerLine, PosLoyaltyPartnerLine);

export default PartnerLine;
