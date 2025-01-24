import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showCreateProductButton() {
        return this.pos.config.module_pos_hr
            ? this.pos.cashier._role === "manager" && super.showCreateProductButton
            : super.showCreateProductButton;
    },
});
