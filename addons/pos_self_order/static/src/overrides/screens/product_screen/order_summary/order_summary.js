import { patch } from "@web/core/utils/patch";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    setup() {
        super.setup();
        this.clickPrintQrMenu = useAsyncLockedMethod(this.clickPrintQrMenu);
    },
    get showPrintOrderQrTicketButton() {
        return (
            this.showUnbookButton() &&
            this.pos.config.self_ordering_mode === "mobile" &&
            this.pos.selectedOrder.table_id
        );
    },
    async clickPrintQrMenu() {
        this.pos.printOrderQrTicket();
    },
});
