import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { enhancedButtons } from "@point_of_sale/app/generic_components/numpad/numpad";

patch(OrderSummary.prototype, {
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
                    this.currentOrder.uiState.lineToRefund ||
                this.currentOrder.isValidNegativeOrder() ||
                this.currentOrder.lines.length === 1
            )
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Negative quantity"),
                body: _t(
                    "You cannot set a negative quantity. If you want to do a refund, you can use the refund button."
                ),
            });
            return false;
        } else if (
            newQuantity > 0 &&
            this.currentOrder.isValidNegativeOrder() &&
            this.currentOrder.lines.length > 1
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Positive quantity"),
                body: _t("You cannot set a positive quantity with a refund order."),
            });
            return false;
        }
        return await super.updateQuantityNumber(newQuantity);
    },
    _handleNegationOnFirstInput(buffer, key, selectedLine) {
        if (
            this.pos.useBlackBoxBe() &&
            buffer === "-0" &&
            key == "-" &&
            this.currentOrder.isValidNegativeOrder()
        ) {
            buffer = selectedLine.get_quantity();
            this.numberBuffer.state.buffer = buffer.toString();
            return buffer;
        }
        return super._handleNegationOnFirstInput(...arguments);
    },
    handleOrderLineQuantityChange(selectedLine, buffer, currentQuantity, lastId) {
        const parsedInput = (buffer && parseFloat(buffer)) || 0;
        if (!this.pos.useBlackBoxBe() || !(currentQuantity < parsedInput)) {
            return super.handleOrderLineQuantityChange(...arguments);
        }
        if (
            parsedInput > 0 &&
            this.currentOrder.isValidNegativeOrder() &&
            this.currentOrder.lines.length > 1
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Positive quantity"),
                body: _t("You cannot set a positive quantity with a refund order."),
            });
        } else {
            this._setValue(buffer);
        }
    },
    async handleDecreaseUnsavedLine(newQuantity) {
        if (!this.pos.useBlackBoxBe()) {
            return await super.handleDecreaseUnsavedLine(newQuantity);
        }
        await this.pos.pushCorrection(this.currentOrder, [
            this.currentOrder.get_selected_orderline(),
        ]);
        const decreasedQuantity = await super.handleDecreaseUnsavedLine(newQuantity);
        await this.pos.pushProFormaOrderLog(this.currentOrder);
        return decreasedQuantity;
    },
    async handleDecreaseLine(newQuantity) {
        if (!this.pos.useBlackBoxBe()) {
            return await super.handleDecreaseLine(newQuantity);
        }
        await this.pos.pushCorrection(this.currentOrder, [
            this.currentOrder.get_selected_orderline(),
        ]);
        const oldTotal = this.currentOrder.get_total_with_tax();
        const decreasedQuantity = await super.handleDecreaseLine(newQuantity);
        await this.pos.increaseCorrectionCounter(oldTotal - this.currentOrder.get_total_with_tax());
        await this.pos.pushProFormaOrderLog(this.currentOrder);
        return decreasedQuantity;
    },
    getNewLine() {
        if (!this.pos.useBlackBoxBe()) {
            return super.getNewLine();
        }
        return this.currentOrder.get_selected_orderline();
    },
    async setLinePrice(line, price) {
        if (!this.pos.useBlackBoxBe()) {
            return await super.setLinePrice(line, price);
        }
        await this.pos.pushCorrection(this.currentOrder, [
            this.currentOrder.get_selected_orderline(),
        ]);
        await super.setLinePrice(line, price);
        await this.pos.pushProFormaOrderLog(this.currentOrder);
    },
    async _getShowDecreaseQuantityPopupButtons() {
        return this.pos.useBlackBoxBe()
            ? enhancedButtons()
            : await super._getShowDecreaseQuantityPopupButtons();
    },
});
