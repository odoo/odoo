import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { AddTbaiRefundReasonPopup } from "@l10n_es_edi_tbai_pos/app/components/popups/add_tbai_refund_reason_popup/add_tbai_refund_reason_popup";
import { qrCodeSrc } from "@point_of_sale/utils";

patch(TicketScreen.prototype, {
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.pos.company.l10n_es_tbai_is_enabled && order.account_move) {
            const payload = await makeAwaitable(this.dialog, AddTbaiRefundReasonPopup, {
                order: destinationOrder,
            });
            if (payload) {
                destinationOrder.l10n_es_tbai_refund_reason = payload.l10n_es_tbai_refund_reason;
                destinationOrder.to_invoice = true;
            }
        }
        await super.addAdditionalRefundInfo(...arguments);
    },
    async print(order) {
        if (
            this.pos.company.l10n_es_tbai_is_enabled &&
            typeof order.id === "number" &&
            !order.l10n_es_pos_tbai_qrsrc
        ) {
            const url = await this.pos.data.call("pos.order", "get_l10n_es_pos_tbai_qrurl", [
                order.id,
            ]);
            order.l10n_es_pos_tbai_qrsrc = url ? qrCodeSrc(url) : undefined;
        }
        return super.print(...arguments);
    },
});
