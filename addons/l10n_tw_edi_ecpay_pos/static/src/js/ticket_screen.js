import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    setPartnerToRefundOrder(partner, destinationOrder) {
        const isTaiwanECPay =
            this.pos.company.country_id?.code === "TW" && this.pos.config.is_ecpay_enabled;
        if (!isTaiwanECPay) {
            super.setPartnerToRefundOrder(partner, destinationOrder);
            return;
        }

        const currentPartner = destinationOrder.get_partner();
        const canSetPartner =
            !currentPartner || currentPartner.id === this.pos.session._default_tw_customer_id;

        if (partner && canSetPartner) {
            destinationOrder.set_partner(partner);
        }
    },
});
