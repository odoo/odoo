/** @odoo-module **/

import { PrintBillButton } from "@pos_restaurant/js/Screens/ProductScreen/ControlButtons/PrintBillButton";
import { patch } from "@web/core/utils/patch";

patch(PrintBillButton.prototype, "pos_proforma.PrintBillButton", {
    async onClick() {
        const _super = this._super;
        let order = this.env.pos.get_order();

        await this.env.pos.push_pro_forma_order(order);
        await _super(...arguments);
    }
});
