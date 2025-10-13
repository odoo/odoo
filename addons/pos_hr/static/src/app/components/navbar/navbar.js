import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { useCheckPin } from "@pos_hr/app/utils/select_cashier_mixin";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.checkPin = useCheckPin();
    },
    get showCreateProductButton() {
        if (!this.pos.config.module_pos_hr || this.pos.employeeIsAdmin) {
            return super.showCreateProductButton;
        } else {
            return false;
        }
    },
    async checkPin(employee = false) {
        return await this.checkPin(...arguments);
    },
    async clickBackend() {
        if (this.pos.config.module_pos_hr) {
            const posUserEmployee = this.pos.models["hr.employee"].find(
                (e) => e.user_id?.id === this.pos.user.id
            );
            if (await this.checkPin(posUserEmployee)) {
                super.clickBackend();
            }
        } else {
            super.clickBackend();
        }
    },
    get showBackend() {
        const cashier = this.pos.getCashierUserId();
        return !this.pos.config.module_pos_hr || (cashier && cashier.id === this.pos.user?.id);
    },
});
