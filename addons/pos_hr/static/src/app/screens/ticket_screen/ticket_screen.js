import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    get showSubPads() {
        return (
            super.showSubPads &&
            (!this.pos.config.module_pos_hr ||
                !this.pos.hasEmployeeRole(["supervised", "restrictive"]))
        );
    },
    shouldHideDeleteButton(order) {
        if (this.pos.hasEmployeeRole(["supervised", "restrictive"])) {
            return true;
        }
        return super.shouldHideDeleteButton(order);
    },
});
