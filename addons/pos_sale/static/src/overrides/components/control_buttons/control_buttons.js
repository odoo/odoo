/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { SaleOrderPopup } from "@pos_sale/components/sale_order_popup/sale_order_popup";

patch(ControlButtons.prototype, {
    async onClickQuotation() {
        await makeAwaitable(this.dialog, SaleOrderPopup, {
            getPayload: (so) => this.pos.onClickSaleOrder(so),
        });
    },
});
