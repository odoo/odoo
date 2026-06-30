import { AddZatcaRefundReasonPopup } from "@l10n_sa_pos/app/add_zatca_refund_reason_popup/add_zatca_refund_reason_popup";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.pos.company.country_id.code === "SA") {
            const payload = await makeAwaitable(this.dialog, AddZatcaRefundReasonPopup, {
                order: destinationOrder,
            });
            if (payload) {
                destinationOrder.l10n_sa_reason = payload.l10n_sa_reason;
                destinationOrder.to_invoice = true;
            }
        }
        return super.addAdditionalRefundInfo(...arguments);
    },
});
