import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    get showJoEdiStatus() {
        return this.pos.config.company_id.l10n_jo_edi_pos_enabled;
    },
    get joEdiStatus() {
        switch (this.order.l10n_jo_edi_pos_state) {
            case "to_send":
                return _t("To Send");
            case "sent":
                return _t("Sent");
            case "demo":
                return _t("Sent (Demo)");
            default:
                return "";
        }
    },
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.pos.config.company_id.country_id.code === "JO") {
            const payload = await makeAwaitable(this.dialog, TextInputPopup, {
                title: _t("JoFotara Return Reason"),
            });
            if (payload) {
                destinationOrder.l10n_jo_edi_pos_return_reason = payload;
            }
        }
        return super.addAdditionalRefundInfo(...arguments);
    },
});
