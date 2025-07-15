import { patch } from "@web/core/utils/patch";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    setup() {
        super.setup();
        this.onClickPrintTableQr = useAsyncLockedMethod(async () => await this.pos.printTableQr());
    },
    get showPrintTableQrButton() {
        return (
            this.showUnbookButton() &&
            this.pos.config.self_ordering_mode === "mobile" &&
            this.pos.selectedOrder.table_id
        );
    },
});
