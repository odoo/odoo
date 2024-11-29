import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";

patch(Chrome.prototype, {
    get showCashMoveButton() {
        const { cashier } = this.pos;
        return super.showCashMoveButton && (!cashier || cashier._role == "manager");
    },
});
