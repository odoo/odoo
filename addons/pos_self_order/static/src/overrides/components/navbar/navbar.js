import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

patch(Navbar.prototype, {
    get showOderTrackerDropdown() {
        return super.showOderTrackerDropdown || this.pos.config.self_ordering_mode === "mobile";
    },
    get showScanButton() {
        return (
            super.showScanButton ||
            (this.pos.config.useDynamicQr && this.pos.router.currentScreen() === "TicketScreen")
        );
    },
});
