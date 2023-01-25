/** @odoo-module */

import { CashierName } from "@point_of_sale/js/ChromeWidgets/CashierName";
import { patch } from "@web/core/utils/patch";
import { SelectCashierMixin } from "@pos_hr/js/SelectCashierMixin";
import { useBarcodeReader } from "@point_of_sale/js/custom_hooks";

patch(CashierName.prototype, "pos_hr.CashierName", {
    ...SelectCashierMixin,
    setup() {
        this._super(...arguments);
        useBarcodeReader({ cashier: this.barcodeCashierAction });
    },
    //@Override
    get avatar() {
        if (this.env.pos.config.module_pos_hr) {
            const cashier = this.env.pos.get_cashier();
            return `/web/image/hr.employee/${cashier.id}/avatar_128`;
        }
        return this._super(...arguments);
    },
    //@Override
    get cssClass() {
        if (this.env.pos.config.module_pos_hr) {
            return { oe_status: true };
        }
        return this._super(...arguments);
    },
});
