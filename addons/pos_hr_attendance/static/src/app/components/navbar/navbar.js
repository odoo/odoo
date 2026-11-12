import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

patch(Navbar.prototype, {
    get mainButton() {
        return this.pos.router.currentScreen() === "AttendanceScreen"
            ? "attendance"
            : super.mainButton;
    },
});
