import { patch } from "@web/core/utils/patch";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";

patch(SelectPartnerButton.prototype, {
    isOverLimit() {
        const partnerInfos = this.pos.getPartnerCredit(this.props.partner);
        return partnerInfos?.overDue && partnerInfos?.useLimit;
    },
});
