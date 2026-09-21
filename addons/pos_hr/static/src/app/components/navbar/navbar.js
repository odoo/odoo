import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showCloseSession() {
        const user = this.pos.getCashierUserId();
        return (
            !this.pos.config.module_pos_hr ||
            this.pos.employeeIsAdmin ||
            Boolean(user && user.id === this.pos.session.user_id?.id)
        );
    },
    get showBackend() {
        const cashier = this.pos.getCashierUserId();
        return !this.pos.config.module_pos_hr || (cashier && cashier.id === this.pos.user?.id);
    },
});
