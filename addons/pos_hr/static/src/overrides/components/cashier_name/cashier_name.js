import { CashierName } from "@point_of_sale/app/navbar/cashier_name/cashier_name";
import { patch } from "@web/core/utils/patch";
import { useCashierSelector } from "@pos_hr/app/select_cashier_mixin";

patch(CashierName.prototype, {
    setup() {
        super.setup(...arguments);
        this.selectCashier = useCashierSelector();
    },
    //@Override
    get avatar() {
        if (this.pos.config.module_pos_hr) {
            const employee = this.pos.cashier.employee;
            if (!(employee && employee.id)) {
                return "";
            }
            return `/web/image/hr.employee.public/${employee.id}/avatar_128`;
        }
        return super.avatar;
    },
    //@Override
    get cssClass() {
        if (this.pos.config.module_pos_hr) {
            return { oe_status: true };
        }
        return super.cssClass;
    },
    get username() {
        return this.pos.cashier?.employee?.name || "";
    },
});
