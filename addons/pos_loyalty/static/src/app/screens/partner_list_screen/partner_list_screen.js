import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);
        // Load the loyalty cards of the partners shown on open so their balances
        // are displayed; freshly fetched partners are handled in getNewPartners.
        this.pos.loadPartnerCards(this.state.initialPartners.map((partner) => partner.id));
    },
    /**
     * Show the balance column so each partner's loyalty points can be displayed.
     * @override
     */
    get isBalanceDisplayed() {
        return this.pos.models["loyalty.program"].length > 0 || super.isBalanceDisplayed;
    },
    async getNewPartners() {
        const partners = await super.getNewPartners();
        await this.pos.loadPartnerCards(partners.map((partner) => partner.id));
        return partners;
    },
});
