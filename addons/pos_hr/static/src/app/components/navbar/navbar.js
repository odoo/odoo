import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
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
        const cashier = this.pos.getCashierUserId();
        return (
            !this.pos.config.module_pos_hr ||
            (cashier && cashier.id === this.pos.session.user_id?.id)
        );
    },
});
