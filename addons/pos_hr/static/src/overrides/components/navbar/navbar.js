import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showCreateProductButton() {
        if (!this.pos.config.module_pos_hr || this.pos.employeeIsAdmin) {
            return super.showCreateProductButton;
        } else {
            return false;
        }
    },
    get showBackend() {
        const cashier = this.pos.get_cashier_user_id();
        return !this.pos.config.module_pos_hr || (cashier && cashier.id === this.pos.user?.id);
    },
});
