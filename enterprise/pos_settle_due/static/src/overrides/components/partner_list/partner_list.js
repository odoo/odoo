import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    get isBalanceDisplayed() {
        return true;
    },
    get partnerInfos() {
        return this.pos.getPartnerCredit(this.props.partner);
    },
    async searchPartner() {
        const partners = await super.searchPartner();
        this.pos.setAllTotalDueOfPartners(partners);
        return partners;
    },
});
