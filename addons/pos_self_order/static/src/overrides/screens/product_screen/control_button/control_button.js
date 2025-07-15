import { patch } from "@web/core/utils/patch";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.onClickPrintTableQr = useAsyncLockedMethod(async () => await this.pos.printTableQr());
    },
    get showPrintTableQrButton() {
        return this.pos.config.self_ordering_mode === "mobile" && this.currentOrder.table_id;
    },
});
