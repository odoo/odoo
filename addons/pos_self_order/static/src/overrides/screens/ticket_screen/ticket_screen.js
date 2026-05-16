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
    getTableTag(order) {
        return super.getTableTag(order) || order?.self_ordering_table_id?.table_number;
    },
    //  Todo: remove in master -->
    getFilteredOrderList() {
        const orders = super.getFilteredOrderList();
        orders.forEach((order) => {
            if (
                ["kiosk", "mobile"].includes(order.source) &&
                !order.online_payment_method_id &&
                !Object.keys(order.last_order_preparation_change.lines).length
            ) {
                order.updateLastOrderChange();
            }
        });
        return orders;
    },
});
