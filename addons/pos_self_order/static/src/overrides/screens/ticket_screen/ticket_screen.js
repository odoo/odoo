import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    getStatus(order) {
        if (
            order.state === "paid" &&
            (order.pos_reference.includes("Kiosk") || order.pos_reference.includes("Self-Order")) &&
            !["ReceiptScreen", "TipScreen"].includes(order.getScreenData().name)
        ) {
            return _t("Paid");
        }
        return super.getStatus(...arguments);
    },
});
