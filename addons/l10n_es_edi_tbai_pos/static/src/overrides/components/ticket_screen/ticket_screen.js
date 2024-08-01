import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AddTbaiRefundReasonPopup } from "@l10n_es_edi_tbai_pos/app/add_tbai_refund_reason_popup/add_tbai_refund_reason_popup";

patch(TicketScreen.prototype, {
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.pos.company.l10n_es_tbai_is_enabled && order.state == "invoiced") {
            const payload = await makeAwaitable(this.dialog, AddTbaiRefundReasonPopup, {
                order: destinationOrder,
            });
            if (payload) {
                destinationOrder.l10n_es_tbai_refund_reason = payload.l10n_es_tbai_refund_reason;
                destinationOrder.to_invoice = true;
            }
        }
        super.addAdditionalRefundInfo(...arguments);
    },
});
