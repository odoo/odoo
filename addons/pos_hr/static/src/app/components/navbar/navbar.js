import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showCreateProductButton() {
        if (!this.pos.config.module_pos_hr) {
            return super.showCreateProductButton;
        } else {
            return this.pos.employeeIsAdmin;
        }
    },
    get showBackendButton() {
        return this.pos.getCashier().user_id?.id == this.pos.user.id;
    },
});
