import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    sendBalance() {
        for (const pm of this.pos.config.payment_method_ids) {
            if (pm.payment_provider === "six") {
                pm.payment_interface?.sendBalance();
            }
        }
    },
});
