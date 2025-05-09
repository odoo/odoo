import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { parseFloat } from "@web/views/fields/parsers";
<<<<<<< c9f7a896d4a076cdcebd8515e733ab3209ed97d9
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
||||||| fdb549742f2be0bd71215dad137cbc59f9adba6b
=======
import { getButtons } from "@point_of_sale/app/generic_components/numpad/numpad";
>>>>>>> 6599e44f18a634504227a85e76dda6e597714ab6

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
        return this.pos.getOrder();
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
<<<<<<< c9f7a896d4a076cdcebd8515e733ab3209ed97d9

    async updateSelectedOrderline({ buffer, key }) {
        const order = this.pos.getOrder();
        const selectedLine = order.getSelectedOrderline();
        // Handling negation of value on first input
||||||| fdb549742f2be0bd71215dad137cbc59f9adba6b

    async updateSelectedOrderline({ buffer, key }) {
        const order = this.pos.get_order();
        const selectedLine = order.get_selected_orderline();
        // Handling negation of value on first input
=======
    handleOrderLineQuantityChange(selectedLine, buffer, currentQuantity, lastId) {
        const parsedInput = (buffer && parseFloat(buffer)) || 0;
        if (lastId != selectedLine.cid || parsedInput < currentQuantity) {
            this._showDecreaseQuantityPopup();
        } else if (currentQuantity < parsedInput) {
            this._setValue(buffer);
        }
    }
    // Handle negation of value on first input
    _handleNegationOnFirstInput(buffer, key, selectedLine) {
>>>>>>> 6599e44f18a634504227a85e76dda6e597714ab6
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
            const currentQuantity = this.pos.getOrder().getSelectedOrderline().getQuantity();

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
                selectedLine.setDiscount(val);
            } else if (numpadMode === "price" && val !== "remove") {
                this.setLinePrice(selectedLine, val);
            }
        }
    }

    setLinePrice(line, price) {
        line.price_type = "manual";
        line.setUnitPrice(price);
    }
    async _getShowDecreaseQuantityPopupButtons() {
        return getButtons();
    }
    async _showDecreaseQuantityPopup() {
        this.numberBuffer.reset();
        const inputNumber = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Set the new quantity"),
            buttons: await this._getShowDecreaseQuantityPopupButtons(),
        });
        const newQuantity = inputNumber && inputNumber !== "" ? parseFloat(inputNumber) : null;
        if (newQuantity !== null) {
<<<<<<< c9f7a896d4a076cdcebd8515e733ab3209ed97d9
            const order = this.pos.getOrder();
            const selectedLine = order.getSelectedOrderline();
            const currentQuantity = selectedLine.getQuantity();
            if (newQuantity >= currentQuantity) {
                selectedLine.setQuantity(newQuantity);
                return true;
||||||| fdb549742f2be0bd71215dad137cbc59f9adba6b
            const selectedLine = this.currentOrder.get_selected_orderline();
            const currentQuantity = selectedLine.get_quantity();
            if (newQuantity >= currentQuantity) {
                selectedLine.set_quantity(newQuantity);
            } else if (newQuantity >= selectedLine.saved_quantity) {
                await this.handleDecreaseUnsavedLine(newQuantity);
            } else {
                await this.handleDecreaseLine(newQuantity);
=======
            const selectedLine = this.currentOrder.get_selected_orderline();
            const currentQuantity = selectedLine.get_quantity();
            if (Math.abs(newQuantity) >= currentQuantity) {
                selectedLine.set_quantity(newQuantity);
            } else if (Math.abs(newQuantity) >= selectedLine.saved_quantity) {
                await this.handleDecreaseUnsavedLine(newQuantity);
            } else {
                await this.handleDecreaseLine(newQuantity);
>>>>>>> 6599e44f18a634504227a85e76dda6e597714ab6
            }
            if (newQuantity >= selectedLine.saved_quantity) {
                selectedLine.setQuantity(newQuantity);
                if (newQuantity == 0) {
                    selectedLine.delete();
                }
                return true;
            }
            const newLine = selectedLine.clone();
            const decreasedQuantity = selectedLine.saved_quantity - newQuantity;
            newLine.order = order;
            newLine.setQuantity(-decreasedQuantity, true);
            selectedLine.setQuantity(selectedLine.saved_quantity);
            order.add_orderline(newLine);
            return true;
        }
        return false;
    }
}
