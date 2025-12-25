import { CashierName } from "@point_of_sale/app/navbar/cashier_name/cashier_name";
import { patch } from "@web/core/utils/patch";
import { useCashierSelector } from "@pos_hr/app/select_cashier_mixin";

patch(CashierName.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.config.module_pos_hr) {
            this.cashierSelector = useCashierSelector();
        }
    },
    //@Override
    get avatar() {
        if (this.pos.config.module_pos_hr) {
            const cashier = this.pos.get_cashier();
            if (!(cashier && cashier.id)) {
                return "";
            }
            return `/web/image/hr.employee.public/${cashier.id}/avatar_128`;
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
    async selectCashier(pin = false, login = false, list = false) {
        return await this.cashierSelector(...arguments);
    },
});
