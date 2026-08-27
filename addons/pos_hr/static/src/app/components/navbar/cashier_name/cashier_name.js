import { CashierName } from "@point_of_sale/app/components/navbar/cashier_name/cashier_name";
import { patch } from "@web/core/utils/patch";

patch(CashierName.prototype, {
    //@Override
    get avatar() {
        if (this.pos.config.module_pos_hr) {
            const cashier = this.pos.accessRight.loggedCashier;
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
    async onCashierClick() {
        if (!this.pos.config.module_pos_hr) {
            return;
        }
        return this.pos.accessRight.selectCashier(false, true, true);
    },
});
