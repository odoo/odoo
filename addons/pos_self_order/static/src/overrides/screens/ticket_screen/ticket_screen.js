import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    getStatus(order) {
        if (!(order.pos_reference || "").includes("Self")) {
            return super.getStatus(order);
        }

        if (order.state === "cancel") {
            return _t("Cancelled");
        } else if (order.finalized) {
            if (order.raw.account_move) {
                return _t("Invoiced");
            }

            return _t("Paid");
        } else {
            return _t("Ongoing");
        }
    },
});
