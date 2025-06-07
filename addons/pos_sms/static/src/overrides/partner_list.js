import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {
    getPhoneSearchTerms() {
        return ["phone_mobile_search"];
    },
});
