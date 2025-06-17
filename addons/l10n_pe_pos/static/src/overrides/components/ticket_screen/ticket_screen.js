import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    setPartnerToRefundOrder(partner, destinationOrder) {
        if (!this.pos.isPeruvianCompany()) {
            return super.setPartnerToRefundOrder(...arguments);
        }
        if (
            partner &&
            (!destinationOrder.getPartner() ||
                destinationOrder.getPartner().id === this.pos.config._consumidor_final_anonimo_id)
        ) {
            return destinationOrder.setPartner(partner);
        }
    },
});
