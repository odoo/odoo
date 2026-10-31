// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async l10nPhApplyDiscountPrivileges() {
        const result = await super.l10nPhApplyDiscountPrivileges(...arguments);
        // The split lines are privileged: the order's discount rewards must
        // no longer apply on them (see LoyaltyReward.getDiscountApplicableLines).
        this.updateRewards();
        return result;
    },
    async l10nPhRemoveDiscountPrivilege() {
        const result = await super.l10nPhRemoveDiscountPrivilege(...arguments);
        // The share is regular again: discount rewards apply on it again.
        this.updateRewards();
        return result;
    },
});
