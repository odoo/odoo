import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    async clock() {
        if (this.pos.useBlackBoxBe()) {
            if (!this.pos.user_session_status) {
                await this.pos.clock(this.pos.printer, true);
            } else {
                await this.pos.clock(this.pos.printer, false);
            }
        }
    },
    get workButtonName() {
        return this.pos.user_session_status ? "Clock out" : "Clock in";
    },
});
