import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    setPartnerToRefundOrder(partner, destinationOrder) {
        const isTaiwanECPay =
            this.pos.company.account_fiscal_country_id?.code === "TW" &&
            this.pos.config.is_ecpay_enabled;
        if (!isTaiwanECPay) {
            super.setPartnerToRefundOrder(partner, destinationOrder);
            return;
        }

        const currentPartner = destinationOrder.getPartner();
        const canSetPartner =
            !currentPartner || currentPartner.id === this.pos.config._tw_walk_in_customer;

        if (partner && canSetPartner) {
            destinationOrder.setPartner(partner);
        }
    },
});
