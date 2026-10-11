import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AddVerifactuRefundReasonPopup } from "@l10n_es_edi_verifactu_pos/app/add_verifactu_refund_reason_popup/add_verifactu_refund_reason_popup";

patch(TicketScreen.prototype, {
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.pos.company.l10n_es_edi_verifactu_required) {
            if (!order.is_to_invoice()) {
                // A PoS order that is not explicitly invoiced is a simplified invoice.
                // Per Spanish regulation, refunds of simplified invoices always use reason R5.
                destinationOrder.l10n_es_edi_verifactu_refund_reason = "R5";
            } else {
                const payload = await makeAwaitable(this.dialog, AddVerifactuRefundReasonPopup, {
                    order: destinationOrder,
                });
                if (payload) {
                    destinationOrder.l10n_es_edi_verifactu_refund_reason =
                        payload.l10n_es_edi_verifactu_refund_reason;
                }
            }
        }
        await super.addAdditionalRefundInfo(...arguments);
    },
});
