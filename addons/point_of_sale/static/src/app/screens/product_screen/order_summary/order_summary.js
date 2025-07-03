import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { parseFloat } from "@web/views/fields/parsers";
import { enhancedButtons } from "@point_of_sale/app/generic_components/numpad/numpad";

export class OrderSummary extends Component {
    static template = "point_of_sale.OrderSummary";
    static components = {
        Orderline,
        OrderWidget,
    };
    static props = {};

    setup() {
        super.setup();
        this.numberBuffer = useService("number_buffer");
        this.dialog = useService("dialog");
        this.pos = usePos();

        this.numberBuffer.use({
            triggerAtInput: (...args) => this.updateSelectedOrderline(...args),
            useWithBarcode: true,
        });
    }

    get currentOrder() {
        return this.pos.get_order();
    }

    async editPackLotLines(line) {
        const isAllowOnlyOneLot = line.product_id.isAllowOnlyOneLot();
        const editedPackLotLines = await this.pos.editLots(
            line.product_id,
            line.getPackLotLinesToEdit(isAllowOnlyOneLot)
        );

        line.editPackLotLines(editedPackLotLines);
    }

    clickLine(ev, orderline) {
        if (ev.detail === 2) {
            clearTimeout(this.singleClick);
            return;
        }
        this.numberBuffer.reset();
        if (!orderline.isSelected()) {
            this.pos.selectOrderLine(this.currentOrder, orderline);
        } else {
            this.singleClick = setTimeout(() => {
                this.pos.get_order().uiState.selected_orderline_uuid = null;
            }, 300);
        }
    }
    handleOrderLineQuantityChange(selectedLine, buffer, currentQuantity, lastId) {
        const parsedInput = (buffer && parseFloat(buffer)) || 0;
        if (lastId != selectedLine.uuid || parsedInput < currentQuantity) {
            this._showDecreaseQuantityPopup();
        } else if (currentQuantity < parsedInput) {
            this._setValue(buffer);
        }
    }
    // Handle negation of value on first input
    _handleNegationOnFirstInput(buffer, key, selectedLine) {
        if (buffer === "-0" && key == "-") {
            if (this.pos.numpadMode === "quantity" && !selectedLine.refunded_orderline_id) {
                buffer = selectedLine.get_quantity() * -1;
            } else if (this.pos.numpadMode === "discount") {
                buffer = selectedLine.get_discount() * -1;
            } else if (this.pos.numpadMode === "price") {
                buffer = selectedLine.get_unit_price() * -1;
            }
            this.numberBuffer.state.buffer = buffer.toString();
        }
        return buffer;
    }
    async updateSelectedOrderline({ buffer, key }) {
        const order = this.pos.get_order();
        const selectedLine = order.get_selected_orderline();
        buffer = this._handleNegationOnFirstInput(buffer, key, selectedLine);
        // This validation must not be affected by `disallowLineQuantityChange`
        if (selectedLine && selectedLine.isTipLine() && this.pos.numpadMode !== "price") {
            /**
             * You can actually type numbers from your keyboard, while a popup is shown, causing
             * the number buffer storage to be filled up with the data typed. So we force the
             * clean-up of that buffer whenever we detect this illegal action.
             */
            this.numberBuffer.reset();
            if (key === "Backspace") {
                this._setValue("remove");
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Cannot modify a tip"),
                    body: _t("Customer tips, cannot be modified directly"),
                });
            }
            return;
        }
        if (
            selectedLine &&
            this.pos.numpadMode === "quantity" &&
            this.pos.disallowLineQuantityChange()
        ) {
            const orderlines = order.lines;
            const lastId = orderlines.length !== 0 && orderlines.at(orderlines.length - 1).uuid;
            const currentQuantity = this.pos.get_order().get_selected_orderline().get_quantity();

            if (selectedLine.noDecrease) {
                this.dialog.add(AlertDialog, {
                    title: _t("Invalid action"),
                    body: _t("You are not allowed to change this quantity"),
                });
                return;
            }

            this.handleOrderLineQuantityChange(
                selectedLine,
                this.numberBuffer.state.buffer,
                currentQuantity,
                lastId
            );
            return;
        } else if (
            selectedLine &&
            this.pos.numpadMode === "discount" &&
            this.pos.restrictLineDiscountChange()
        ) {
            this.numberBuffer.reset();
            const inputNumber = await makeAwaitable(this.dialog, NumberPopup, {
                startingValue: selectedLine.get_discount() || 10,
                title: _t("Set the new discount"),
            });
            if (inputNumber) {
                await this.pos.setDiscountFromUI(selectedLine, inputNumber);
            }
            return;
        } else if (
            selectedLine &&
            this.pos.numpadMode === "price" &&
            this.pos.restrictLinePriceChange()
        ) {
            this.numberBuffer.reset();
            const inputNumber = await makeAwaitable(this.dialog, NumberPopup, {
                startingValue: selectedLine.get_unit_price(),
                title: _t("Set the new price"),
            });
            if (inputNumber) {
                await this.setLinePrice(selectedLine, inputNumber);
            }
            return;
        }
        const val = buffer === null ? "remove" : buffer;
        this._setValue(val);
        if (val == "remove") {
            this.numberBuffer.reset();
            this.pos.numpadMode = "quantity";
        }
    }

    _setValue(val) {
        const { numpadMode } = this.pos;
        let selectedLine = this.currentOrder.get_selected_orderline();
        if (selectedLine) {
            if (numpadMode === "quantity") {
                if (selectedLine.combo_parent_id) {
                    selectedLine = selectedLine.combo_parent_id;
                }
                if (val === "remove") {
                    this.currentOrder.removeOrderline(selectedLine);
                } else {
                    const result = selectedLine.set_quantity(
                        val,
                        Boolean(selectedLine.combo_line_ids?.length)
                    );
                    for (const line of selectedLine.combo_line_ids) {
                        line.set_quantity(val, true);
                    }
                    if (result !== true) {
                        this.dialog.add(AlertDialog, result);
                        this.numberBuffer.reset();
                    }
                }
            } else if (numpadMode === "discount" && val !== "remove") {
                this.pos.setDiscountFromUI(selectedLine, val);
            } else if (numpadMode === "price" && val !== "remove") {
                this.setLinePrice(selectedLine, val);
            }
        }
    }

    async setLinePrice(line, price) {
        line.price_type = "manual";
        line.set_unit_price(price);
    }
    async _getShowDecreaseQuantityPopupButtons() {
        return enhancedButtons();
    }
    async _showDecreaseQuantityPopup() {
        this.numberBuffer.reset();
        const inputNumber = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Set the new quantity"),
            buttons: await this._getShowDecreaseQuantityPopupButtons(),
        });
        if (inputNumber) {
            const newQuantity = inputNumber && inputNumber !== "" ? parseFloat(inputNumber) : null;
            return await this.updateQuantityNumber(newQuantity);
        }
    }
    async updateQuantityNumber(newQuantity) {
        if (newQuantity !== null) {
            const selectedLine = this.currentOrder.get_selected_orderline();
            const currentQuantity = selectedLine.get_quantity();
            if (Math.abs(newQuantity) >= currentQuantity) {
                selectedLine.set_quantity(newQuantity);
            } else if (Math.abs(newQuantity) >= selectedLine.saved_quantity) {
                await this.handleDecreaseUnsavedLine(newQuantity);
            } else {
                await this.handleDecreaseLine(newQuantity);
            }
            return true;
        }
        return false;
    }
    async handleDecreaseUnsavedLine(newQuantity) {
        const selectedLine = this.currentOrder.get_selected_orderline();
        const decreaseQuantity = selectedLine.get_quantity() - newQuantity;
        selectedLine.set_quantity(newQuantity);
        if (newQuantity == 0) {
            selectedLine.delete();
        }
        return decreaseQuantity;
    }
    async handleDecreaseLine(newQuantity) {
        const selectedLine = this.currentOrder.get_selected_orderline();
        let current_saved_quantity = 0;
        for (const line of this.currentOrder.lines) {
            if (line === selectedLine) {
                current_saved_quantity += line.saved_quantity;
            } else if (
                line.product_id.id === selectedLine.product_id.id &&
                line.get_unit_price() === selectedLine.get_unit_price()
            ) {
                current_saved_quantity += line.qty;
            }
        }
        const newLine = this.getNewLine();
        const decreasedQuantity = current_saved_quantity - newQuantity;
        if (decreasedQuantity != 0) {
            newLine.set_quantity(-decreasedQuantity + newLine.get_quantity(), true);
        }
        if (newLine !== selectedLine && selectedLine.saved_quantity != 0) {
            selectedLine.set_quantity(selectedLine.saved_quantity);
        }
        return decreasedQuantity;
    }
    getNewLine() {
        const selectedLine = this.currentOrder.get_selected_orderline();
        const sign = selectedLine.get_quantity() > 0 ? 1 : -1;
        let newLine = selectedLine;
        if (selectedLine.saved_quantity != 0) {
            for (const line of selectedLine.order_id.lines) {
                if (
                    line.product_id.id === selectedLine.product_id.id &&
                    line.get_unit_price() === selectedLine.get_unit_price() &&
                    line.get_quantity() * sign < 0 &&
                    line !== selectedLine
                ) {
                    return line;
                }
            }
            const data = selectedLine.serialize();
            delete data.uuid;
            newLine = this.pos.models["pos.order.line"].create(
                {
                    ...data,
                    refunded_orderline_id: selectedLine.refunded_orderline_id,
                },
                false,
                true
            );
            newLine.set_quantity(0);
        }
        return newLine;
    }
}
