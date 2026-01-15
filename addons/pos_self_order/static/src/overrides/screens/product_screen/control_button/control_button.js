import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.clickPrintQrMenu = useAsyncLockedMethod(this.clickPrintQrMenu);
    },
    get showPrintOrderQrTicketButton() {
        return (
            this.pos.config.module_pos_restaurant && this.pos.config.self_ordering_mode === "mobile"
        );
    },
    async clickPrintQrMenu() {
        this.dialog.closeAll();
        this.pos.printOrderQrTicket();
    },
});
