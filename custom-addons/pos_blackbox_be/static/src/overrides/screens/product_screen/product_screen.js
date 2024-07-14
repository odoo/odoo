/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
import { Order } from "@point_of_sale/app/store/models";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        if (
            this.pos.useBlackBoxBe() &&
            this.controlButtons.map((cb) => cb.name).includes("DiscountButton")
        ) {
            this.controlButtons.find(
                (cb) => cb.name === "DiscountButton"
            ).component.prototype.apply_discount = async (pc) => {
                try {
                    const order = this.pos.get_order();
                    const lines = order.get_orderlines();
                    this.pos.multiple_discount = true;

                    await order.pushProFormaRefundOrder(); //push the pro forma refund

                    for (const line of lines) {
                        this.pos.setDiscountFromUI(line, pc);
                    }
                    await this.pos.pushProFormaOrder(order, true); //push the pro forma order
                } finally {
                    this.pos.multiple_discount = false;
                }
            };
        }
    },
    _setValue(val) {
        if (this.currentOrder.get_selected_orderline()) {
            // Do not allow to sent line with a quantity of 5 numbers.
            if (this.pos.useBlackBoxBe() && this.pos.numpadMode === "quantity" && val > 9999) {
                val = 9999;
            }
        }
        super._setValue(val);
    },
    async updateQuantityNumber(newQuantity) {
        if (!this.pos.useBlackBoxBe()) {
            return await super.updateQuantityNumber(newQuantity);
        }
        if (newQuantity === null) {
            return false;
        }
        if (newQuantity > 9999) {
            newQuantity = 9999;
        }
        if (
            newQuantity < 0 &&
            !(
                this.currentOrder.get_selected_orderline().refunded_orderline_id in
                this.pos.toRefundLines
            )
        ) {
            this.popup.add(ErrorPopup, {
                title: _t("Negative quantity"),
                body: _t(
                    "You cannot set a negative quantity. If you want to do a refund, you can use the refund button."
                ),
            });
            return false;
        }
        return await super.updateQuantityNumber(newQuantity);
    },
    async handleDecreaseUnsavedLine(newQuantity) {
        if (this.pos.useBlackBoxBe()) {
            await this.pos.pushProFormaOrder(this.currentOrder, true);
        }
        const refund_line = this.currentOrder.get_selected_orderline().clone();
        refund_line.order = this.currentOrder;
        const decreasedQuantity = await super.handleDecreaseUnsavedLine(newQuantity);
        if (this.pos.useBlackBoxBe()) {
            const clonedOrder = new Order(
                { env: this.env },
                { pos: this.pos, json: this.currentOrder.export_as_JSON() }
            );
            for (const line of [...clonedOrder.orderlines]) {
                clonedOrder.removeOrderline(line);
            }
            refund_line.set_quantity(-decreasedQuantity);
            clonedOrder.add_orderline(refund_line);
            clonedOrder.server_id = this.currentOrder.server_id;
            await this.pos.pushProFormaOrderLog(clonedOrder); //push the pro forma refund
            await this.pos.pushProFormaOrder(this.currentOrder, true); //push the pro forma order
        }
    },
    async handleDecreaseLine(newQuantity) {
        const refund_line = this.currentOrder.get_selected_orderline().clone();
        refund_line.order = this.currentOrder;
        const decreasedQuantity = await super.handleDecreaseLine(newQuantity);
        if (this.pos.useBlackBoxBe()) {
            const clonedOrder = new Order(
                { env: this.env },
                { pos: this.pos, json: this.currentOrder.export_as_JSON() }
            );
            for (const line of [...clonedOrder.orderlines]) {
                clonedOrder.removeOrderline(line);
            }
            refund_line.set_quantity(-decreasedQuantity);
            clonedOrder.add_orderline(refund_line);
            clonedOrder.server_id = this.currentOrder.server_id;
            await this.pos.pushProFormaOrderLog(clonedOrder); //push the pro forma refund
            await this.pos.pushProFormaOrder(this.currentOrder, true); //push the pro forma order
        }
    },
    getNewLine() {
        if (!this.pos.useBlackBoxBe()) {
            return super.getNewLine();
        }
        return this.currentOrder.get_selected_orderline();
    },
});
