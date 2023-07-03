/** @odoo-module */

import { CashierName } from "@point_of_sale/app/navbar/cashier_name/cashier_name";
import { patch } from "@web/core/utils/patch";
import { useCashierSelector } from "@pos_hr/js/SelectCashierMixin";

patch(CashierName.prototype, "pos_hr.CashierName", {
    setup() {
        this._super(...arguments);
        this.selectCashier = useCashierSelector();
    },
    //@Override
    get avatar() {
        if (this.pos.config.module_pos_hr) {
            const cashier = this.pos.get_cashier();
            return `/web/image/hr.employee/${cashier.id}/avatar_128`;
        }
        return this._super(...arguments);
    },
    //@Override
    get cssClass() {
        if (this.pos.config.module_pos_hr) {
            return { oe_status: true };
        }
        return this._super(...arguments);
    },
});
