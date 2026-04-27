import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    showBrazilianEDIStatus() {
        return this.pos.config.l10n_br_is_nfce && this.state.filter === "SYNCED";
    },
    getBrazilianEDIStatus() {
        switch (this.order.l10n_br_last_avatax_status) {
            case "pending":
                return _t("Pending");
            case "accepted":
                return _t("Accepted");
            case "error":
                return _t("Error");
            case "cancelled":
                return _t("Cancelled");
            default:
                return "";
        }
    },

    // @override
    postRefund(destinationOrder) {
        if (this.pos.config.l10n_br_is_nfce) {
            destinationOrder.set_to_invoice(true);
            this.pos.showScreen("PaymentScreen", { orderUuid: destinationOrder.uuid });

            // A partner will be required for refunds. Prompt the user to select one.
            if (!destinationOrder.get_partner()) {
                this.pos.selectPartner();
            }
        }
        return super.postRefund(...arguments);
    },
});
