import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { parseFloat } from "@web/views/fields/parsers";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";

export class OrderSummary extends Component {
    static template = "point_of_sale.OrderSummary";
    static components = {
        Orderline,
        OrderDisplay,
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
        return this.pos.selectedOrder;
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
                this.pos.getOrder().uiState.selected_orderline_uuid = null;
            }, 300);
        }
    }

    async updateSelectedOrderline({ buffer, key }) {
        const order = this.pos.getOrder();
        const selectedLine = order.getSelectedOrderline();
        // Handling negation of value on first input
        if (buffer === "-0" && key == "-") {
            if (this.pos.numpadMode === "quantity" && !selectedLine.refunded_orderline_id) {
                buffer = selectedLine.getQuantity() * -1;
            } else if (this.pos.numpadMode === "discount") {
                buffer = selectedLine.getDiscount() * -1;
            } else if (this.pos.numpadMode === "price") {
                buffer = selectedLine.getUnitPrice() * -1;
            }
            this.numberBuffer.state.buffer = buffer.toString();
        }
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
            await this._showDecreaseQuantityPopup();
            if (selectedLine.getQuantity() === 0) {
                const val = buffer === null ? "remove" : buffer;
                this._setValue(val);
            }
            return;
        } else if (
            selectedLine &&
            this.pos.numpadMode === "discount" &&
            this.pos.restrictLineDiscountChange()
        ) {
            this.numberBuffer.reset();
            const inputNumber = await makeAwaitable(this.dialog, NumberPopup, {
                startingValue: selectedLine.getDiscount() || 10,
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
                startingValue: selectedLine.getUnitPrice(),
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
        let selectedLine = this.currentOrder.getSelectedOrderline();
        if (selectedLine) {
            if (numpadMode === "quantity") {
                if (selectedLine.combo_parent_id) {
                    selectedLine = selectedLine.combo_parent_id;
                }
                if (val === "remove") {
                    this.currentOrder.removeOrderline(selectedLine);
                } else {
                    const result = selectedLine.setQuantity(
                        val,
                        Boolean(selectedLine.combo_line_ids?.length)
                    );
                    for (const line of selectedLine.combo_line_ids) {
                        line.setQuantity(val, true);
                    }
                    if (result !== true) {
                        this.dialog.add(AlertDialog, result);
                        this.numberBuffer.reset();
                    }
                }
            } else if (numpadMode === "discount" && val !== "remove") {
                if (selectedLine.combo_parent_id) {
                    selectedLine = selectedLine.combo_parent_id;
                }
                this.pos.setDiscountFromUI(selectedLine, val);
            } else if (numpadMode === "price" && val !== "remove") {
                this.setLinePrice(selectedLine, val);
            }
        }
    }

    async setLinePrice(line, price) {
        line.price_type = "manual";
        line.setUnitPrice(price);
    }

    async _showDecreaseQuantityPopup() {
        this.numberBuffer.reset();
        const inputNumber = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Set the new quantity"),
        });
        if (inputNumber) {
            const newQuantity = inputNumber && inputNumber !== "" ? parseFloat(inputNumber) : null;
            return await this.updateQuantityNumber(newQuantity);
        }
    }
    async updateQuantityNumber(newQuantity) {
        if (newQuantity !== null) {
            const selectedLine = this.currentOrder.getSelectedOrderline();
            const currentQuantity = selectedLine.getQuantity();
            if (newQuantity >= currentQuantity) {
                selectedLine.setQuantity(newQuantity);
            } else if (newQuantity >= selectedLine.uiState.savedQuantity) {
                await this.handleDecreaseUnsavedLine(newQuantity);
            } else {
                await this.handleDecreaseLine(newQuantity);
            }
            return true;
        }
        return false;
    }
    async handleDecreaseUnsavedLine(newQuantity) {
        const selectedLine = this.currentOrder.getSelectedOrderline();
        const decreaseQuantity = selectedLine.getQuantity() - newQuantity;
        selectedLine.setQuantity(newQuantity);
        return decreaseQuantity;
    }
    async handleDecreaseLine(newQuantity) {
        const selectedLine = this.currentOrder.getSelectedOrderline();
        let current_saved_quantity = 0;
        for (const line of this.currentOrder.lines) {
            if (line === selectedLine) {
                current_saved_quantity += line.uiState.savedQuantity;
            } else if (
                line.product_id.id === selectedLine.product_id.id &&
                line.getUnitPrice() === selectedLine.getUnitPrice()
            ) {
                current_saved_quantity += line.qty;
            }
        }
        const newLine = this.getNewLine();
        const decreasedQuantity = current_saved_quantity - newQuantity;
        if (decreasedQuantity != 0) {
            newLine.setQuantity(-decreasedQuantity + newLine.getQuantity(), true);
        }
        if (newLine !== selectedLine && selectedLine.uiState.savedQuantity != 0) {
            selectedLine.setQuantity(selectedLine.uiState.savedQuantity);
        }
        return decreasedQuantity;
    }
    getNewLine() {
        const selectedLine = this.currentOrder.getSelectedOrderline();
        const sign = selectedLine.getQuantity() > 0 ? 1 : -1;
        let newLine = selectedLine;
        if (selectedLine.uiState.savedQuantity != 0) {
            for (const line of selectedLine.order_id.lines) {
                if (
                    line.product_id.id === selectedLine.product_id.id &&
                    line.getUnitPrice() === selectedLine.getUnitPrice() &&
                    line.getQuantity() * sign < 0 &&
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
            newLine.setQuantity(0);
        }
        return newLine;
    }
}
