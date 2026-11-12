import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    get showEtaStatus() {
        return this.pos.config.l10n_eg_edi_pos_enable;
    },
    etaStatus(order) {
        switch (order?.l10n_eg_edi_pos_state) {
            case "to_send":
                return _t("To Send");
            case "sent":
                return _t("Sent");
            case "sent_test":
                return _t("Sent (Test)");
            case "error":
                return _t("Error");
            case "error_test":
                return _t("Error (Test)");
            case "rejected":
                return _t("Rejected");
            case "rejected_test":
                return _t("Rejected (Test)");
            default:
                return "";
        }
    },
    async onDoRefund() {
        this.l10nEgEdiPosRefundReason = false;
        const order = this.getSelectedOrder();
        const willRefund =
            order &&
            (this._doesOrderHaveSoleItem(order)
                ? this._prepareAutoRefundOnOrder(order)
                : this.getHasItemsToRefund());
        if (this.pos.config.l10n_eg_edi_pos_enable && willRefund) {
            const reason = (
                await makeAwaitable(this.dialog, TextInputPopup, {
                    title: _t("Refund Reason"),
                    rows: 3,
                })
            )?.trim();
            if (!reason) {
                return;
            }
            this.l10nEgEdiPosRefundReason = reason;
        }
        return super.onDoRefund(...arguments);
    },
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.l10nEgEdiPosRefundReason) {
            destinationOrder.l10n_eg_edi_pos_refund_reason = this.l10nEgEdiPosRefundReason;
        }
        return super.addAdditionalRefundInfo(...arguments);
    },
});
