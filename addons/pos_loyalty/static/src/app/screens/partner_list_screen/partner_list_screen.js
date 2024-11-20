import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    /**
     * Needs to be set to true to show the loyalty points in the partner list.
     * @override
     */
    get isBalanceDisplayed() {
        return true;
    },

    async searchPartner() {
        const res = await super.searchPartner();
        const coupons = await this.pos.fetchCoupons([
            ["partner_id", "in", res.map((partner) => partner.id)],
            ["program_id.active", "=", true],
        ]);
        this.pos.computePartnerCouponIds(coupons);
        return res;
    },
});
