import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showEditPlanButton() {
        if (
            this.pos.config.module_pos_restaurant &&
            (!this.pos.config.module_pos_hr || this.pos.employeeIsAdmin)
        ) {
            return super.showEditPlanButton;
        } else {
            return false;
        }
    },
});
