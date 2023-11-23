/** @odoo-module */

import { ControlButtonsMixin } from "@point_of_sale/app/utils/control_buttons_mixin";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { parseFloat } from "@web/views/fields/parsers";
import { _t } from "@web/core/l10n/translation";

import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ControlButtonPopup } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons_popup";
import { ConnectionLostError } from "@web/core/network/rpc_service";

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onMounted, useExternalListener, useState } from "@odoo/owl";
import { ErrorBarcodePopup } from "@point_of_sale/app/barcode/error_popup/barcode_error_popup";

import { Numpad } from "@point_of_sale/app/generic_components/numpad/numpad";
import { ProductsWidget } from "@point_of_sale/app/screens/product_screen/product_list/product_list";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
export class ProductScreen extends ControlButtonsMixin(Component) {
    static template = "point_of_sale.ProductScreen";
    static components = {
        ActionpadWidget,
        Numpad,
        ProductsWidget,
        Orderline,
        OrderWidget,
    };
    static numpadActionName = _t("Payment");

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.notification = useService("pos_notification");
        this.numberBuffer = useService("number_buffer");
        this.state = useState({
            showProductReminder: false,
        });
        onMounted(this.onMounted);
        useExternalListener(window, "click", this.clickEvent.bind(this));

        useBarcodeReader({
            product: this._barcodeProductAction,
            quantity: this._barcodeProductAction,
            weight: this._barcodeProductAction,
            price: this._barcodeProductAction,
            client: this._barcodePartnerAction,
            discount: this._barcodeDiscountAction,
            gs1: this._barcodeGS1Action,
        });

        // Call `reset` when the `onMounted` callback in `numberBuffer.use` is done.
        // We don't do this in the `mounted` lifecycle method because it is called before
        // the callbacks in `onMounted` hook.
        onMounted(() => this.numberBuffer.reset());
        this.numberBuffer.use({
            triggerAtInput: (...args) => this.updateSelectedOrderline(...args),
            useWithBarcode: true,
        });
    }
    onMounted() {
        this.pos.openCashControl();
    }

    getNumpadButtons() {
        return [
            { value: "1" },
            { value: "2" },
            { value: "3" },
            { value: "quantity", text: "Qty" },
            { value: "4" },
            { value: "5" },
            { value: "6" },
            { value: "discount", text: "% Disc", disabled: !this.pos.config.manual_discount },
            { value: "7" },
            { value: "8" },
            { value: "9" },
            { value: "price", text: "Price", disabled: !this.pos.cashierHasPriceControlRights() },
            { value: "-", text: "+/-" },
            { value: "0" },
            { value: this.env.services.localization.decimalPoint },
            // Unicode: https://www.compart.com/en/unicode/U+232B
            { value: "Backspace", text: "⌫" },
        ].map((button) => ({
            ...button,
            class: this.pos.numpadMode === button.value ? "active border-primary" : "",
        }));
    }
    onNumpadClick(buttonValue) {
        if (["quantity", "discount", "price"].includes(buttonValue)) {
            this.numberBuffer.capture();
            this.numberBuffer.reset();
            this.pos.numpadMode = buttonValue;
            return;
        }
        this.numberBuffer.sendKey(buttonValue);
    }

    selectLine(orderline) {
        this.numberBuffer.reset();
        this.currentOrder.select_orderline(orderline);
    }

    clickEvent(e) {
        if (!this.ui.isSmall) {
            return;
        }

        const isProductCard = (() => {
            let element = e.target;
            // 3 because product DOM dept is 3
            for (let i = 0; i < 3; i++) {
                if (element.classList.contains("product")) {
                    return true;
                } else {
                    element = element.parentElement;
                }
            }
            return false;
        })();

        this.state.showProductReminder =
            this.currentOrder &&
            this.currentOrder.get_selected_orderline() &&
            this.selectedOrderlineQuantity &&
            isProductCard;
    }

    /**
     * To be overridden by modules that checks availability of
     * connected scale.
     * @see _onScaleNotAvailable
     */
    get partner() {
        return this.currentOrder ? this.currentOrder.get_partner() : null;
    }
    get currentOrder() {
        return this.pos.get_order();
    }
    get total() {
        return this.env.utils.formatCurrency(this.currentOrder?.get_total_with_tax() ?? 0);
    }
    get items() {
        return this.currentOrder.orderlines?.reduce((items, line) => items + line.quantity, 0) ?? 0;
    }
    async updateSelectedOrderline({ buffer, key }) {
        const order = this.pos.get_order();
        const selectedLine = order.get_selected_orderline();
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
                this.popup.add(ErrorPopup, {
                    title: _t("Cannot modify a tip"),
                    body: _t("Customer tips, cannot be modified directly"),
                });
            }
            return;
        }
        if (this.pos.numpadMode === "quantity" && selectedLine?.isPartOfCombo()) {
            if (key === "Backspace") {
                this._setValue("remove");
            } else {
                this.popup.add(ErrorPopup, {
                    title: _t("Invalid action"),
                    body: _t(
                        "The quantity of a combo item cannot be changed. A combo can only be deleted."
                    ),
                });
            }
            return;
        }
        if (selectedLine && this.pos.numpadMode === "quantity" && this.pos.disallowLineQuantityChange()) {
            const orderlines = order.orderlines;
            const lastId = orderlines.length !== 0 && orderlines.at(orderlines.length - 1).cid;
            const currentQuantity = this.pos.get_order().get_selected_orderline().get_quantity();

            if (selectedLine.noDecrease) {
                this.popup.add(ErrorPopup, {
                    title: _t("Invalid action"),
                    body: _t("You are not allowed to change this quantity"),
                });
                return;
            }
            const parsedInput = (buffer && parseFloat(buffer)) || 0;
            if (lastId != selectedLine.cid) {
                this._showDecreaseQuantityPopup();
            } else if (currentQuantity < parsedInput) {
                this._setValue(buffer);
            } else if (parsedInput < currentQuantity) {
                this._showDecreaseQuantityPopup();
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
        const selectedLine = this.currentOrder.get_selected_orderline();
        if (selectedLine) {
            if (numpadMode === "quantity") {
                if (val === "remove") {
                    this.currentOrder.removeOrderline(selectedLine);
                } else {
                    const result = selectedLine.set_quantity(val);
                    if (!result) {
                        this.numberBuffer.reset();
                    }
                }
            } else if (numpadMode === "discount") {
                selectedLine.set_discount(val);
            } else if (numpadMode === "price") {
                selectedLine.price_type = "manual";
                selectedLine.set_unit_price(val);
            }
        }
    }
    async _getProductByBarcode(code) {
        let product = this.pos.db.get_product_by_barcode(code.base_code);
        if (!product) {
            // find the barcode in the backend
            const { product_id = [], packaging = [] } = await this.orm.silent.call(
                "pos.session",
                "find_product_by_barcode",
                [odoo.pos_session_id, code.base_code]
            );
            if (product_id.length) {
                await this.pos._addProducts(product_id, false);
                if (packaging.length) {
                    this.pos.db.add_packagings(packaging);
                }
                // assume that the result is unique.
                product = this.pos.db.get_product_by_id(product_id[0]);
            }
        }
        return product;
    }
    async _barcodeProductAction(code) {
        const product = await this._getProductByBarcode(code);
        if (!product) {
            return this.popup.add(ErrorBarcodePopup, { code: code.base_code });
        }
        const options = await product.getAddProductOptions(code);
        // Do not proceed on adding the product when no options is returned.
        // This is consistent with clickProduct.
        if (!options) {
            return;
        }

        // update the options depending on the type of the scanned code
        if (code.type === "price") {
            Object.assign(options, {
                price: code.value,
                extras: {
                    price_type: "manual",
                },
            });
        } else if (code.type === "weight" || code.type === "quantity") {
            Object.assign(options, {
                quantity: code.value,
                merge: false,
            });
        } else if (code.type === "discount") {
            Object.assign(options, {
                discount: code.value,
                merge: false,
            });
        }
        this.currentOrder.add_product(product, options);
        this.numberBuffer.reset();
    }
    async _getPartnerByBarcode(code) {
        let partner = this.pos.db.get_partner_by_barcode(code.code);
        if (!partner) {
            // find the partner in the backend by the barcode
            const foundPartnerIds = await this.orm.search("res.partner", [
                ["barcode", "=", code.code],
            ]);
            if (foundPartnerIds.length) {
                await this.pos._loadPartners(foundPartnerIds);
                // assume that the result is unique.
                partner = this.pos.db.get_partner_by_id(foundPartnerIds[0]);
            }
        }
        return partner;
    }
    async _barcodePartnerAction(code) {
        const partner = await this._getPartnerByBarcode(code);
        if (partner) {
            if (this.currentOrder.get_partner() !== partner) {
                this.currentOrder.set_partner(partner);
            }
            return;
        }
        return this.popup.add(ErrorBarcodePopup, { code: code.base_code });
    }
    _barcodeDiscountAction(code) {
        var last_orderline = this.currentOrder.get_last_orderline();
        if (last_orderline) {
            last_orderline.set_discount(code.value);
        }
    }
    async _parseElementsFromGS1(parsed_results) {
        const productBarcode = parsed_results.find((element) => element.type === "product");
        const lotBarcode = parsed_results.find((element) => element.type === "lot");
        const product = await this._getProductByBarcode(productBarcode);
        return { product, lotBarcode, customProductOptions: {} };
    }
    /**
     * Add a product to the current order using the product identifier and lot number from parsed results.
     * This function retrieves the product identifier and lot number from the `parsed_results` parameter.
     * It then uses these values to retrieve the product and add it to the current order.
     */
    async _barcodeGS1Action(parsed_results) {
        const { product, lotBarcode, customProductOptions } = await this._parseElementsFromGS1(
            parsed_results
        );
        if (!product) {
            const productBarcode = parsed_results.find((element) => element.type === "product");
            return this.popup.add(ErrorBarcodePopup, { code: productBarcode.base_code });
        }
        const options = await product.getAddProductOptions(lotBarcode);
        await this.currentOrder.add_product(product, { ...options, ...customProductOptions });
        this.numberBuffer.reset();
    }
    async displayAllControlPopup() {
        await this.popup.add(ControlButtonPopup, {
            controlButtons: this.controlButtons,
        });
    }
    async _showDecreaseQuantityPopup() {
        this.numberBuffer.reset();
        const { confirmed, payload: inputNumber } = await this.popup.add(NumberPopup, {
            startingValue: 0,
            title: _t("Set the new quantity"),
        });
        const newQuantity = inputNumber && inputNumber !== "" ? parseFloat(inputNumber) : null;
        if (confirmed && newQuantity !== null) {
            const order = this.pos.get_order();
            const selectedLine = order.get_selected_orderline();
            const currentQuantity = selectedLine.get_quantity();
            if (newQuantity >= currentQuantity) {
                selectedLine.set_quantity(newQuantity);
                return true;
            }
            if (newQuantity >= selectedLine.saved_quantity) {
                selectedLine.set_quantity(newQuantity);
                if (newQuantity == 0) {
                    order._unlinkOrderline(selectedLine);
                }
                return true;
            }
            const newLine = selectedLine.clone();
            const decreasedQuantity = selectedLine.saved_quantity - newQuantity;
            newLine.order = order;
            newLine.set_quantity(-decreasedQuantity, true);
            selectedLine.set_quantity(selectedLine.saved_quantity);
            order.add_orderline(newLine);
            return true;
        }
        return false;
    }
    get selectedOrderlineQuantity() {
        return this.currentOrder.get_selected_orderline()?.get_quantity_str();
    }
    get selectedOrderlineDisplayName() {
        return this.currentOrder.get_selected_orderline()?.get_full_product_name();
    }
    get selectedOrderlineTotal() {
        return this.env.utils.formatCurrency(
            this.currentOrder.get_selected_orderline()?.get_display_price()
        );
    }
    /**
     * This getter is used to restart the animation on the product-reminder.
     * When the information present on the product-reminder will change,
     * the key will change and thus a new product-reminder will be created
     * and the old one will be garbage collected leading to the animation
     * being retriggered.
     */
    get animationKey() {
        return [
            this.currentOrder.get_selected_orderline()?.uuid,
            this.selectedOrderlineQuantity,
            this.selectedOrderlineDisplayName,
            this.selectedOrderlineTotal,
        ].join(",");
    }

    get showProductReminder() {
        return this.currentOrder.get_selected_orderline() && this.selectedOrderlineQuantity;
    }

    primaryPayButton() {
        return !this.currentOrder.is_empty();
    }
    // FIXME POSREF this is dead code, check if we need the business logic that's left in here
    // If we do it should be in the model.
    async onClickPay() {
        if (this.pos.get_order().server_id) {
            try {
                const isPaid = await this.orm.call("pos.order", "is_already_paid", [
                    this.pos.get_order().server_id,
                ]);
                if (isPaid) {
                    const searchDetails = {
                        fieldName: "RECEIPT_NUMBER",
                        searchTerm: this.pos.get_order().uid,
                    };
                    this.pos.showScreen("TicketScreen", {
                        ui: { filter: "SYNCED", searchDetails },
                    });
                    this.notification.add(_t("The order has been already paid."), 3000);
                    this.pos.removeOrder(this.pos.get_order(), false);
                    this.pos.add_new_order();
                    return;
                }
            } catch (error) {
                if (!(error instanceof ConnectionLostError)) {
                    throw error;
                }
                // Reject error in a separate stack to display the offline popup, but continue the flow
                Promise.reject(error);
            }
        }
        this.currentOrder.pay();
    }
    switchPane() {
        this.pos.switchPane();
    }
}

registry.category("pos_screens").add("ProductScreen", ProductScreen);
