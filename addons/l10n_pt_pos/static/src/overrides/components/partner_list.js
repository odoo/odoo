/** @odoo-module */

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    getPartners(partners) {
        const result = super.getPartners(...arguments);
        if (!this.pos.isPortugueseCompany() || this.state.query?.trim()) {
            return result;
        }
        const index = result.findIndex(
            (partner) => partner.id === this.pos.config._l10n_pt_final_consumer_id
        );
        if (index > 0) {
            const [finalConsumer] = result.splice(index, 1);
            result.unshift(finalConsumer);
        }
        return result;
    },
});
