/** @odoo-module */

import { ControlButtonsMixin } from "@point_of_sale/js/ControlButtonsMixin";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useBarcodeReader } from "@point_of_sale/app/barcode_reader_hook";
import { parseFloat } from "@web/views/fields/parsers";
import { _lt } from "@web/core/l10n/translation";

import { NumberPopup } from "@point_of_sale/js/Popups/NumberPopup";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { ControlButtonPopup } from "@point_of_sale/js/Popups/ControlButtonPopup";
import { ConnectionLostError } from "@web/core/network/rpc_service";

import { usePos } from "@point_of_sale/app/pos_hook";
import { Component, onMounted, useState } from "@odoo/owl";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";
import { ErrorBarcodePopup } from "@point_of_sale/js/Popups/ErrorBarcodePopup";

import { MobileOrderWidget } from "../../Misc/MobileOrderWidget";
import { NumpadWidget } from "./NumpadWidget";
import { OrderWidget } from "./OrderWidget";
import { ProductsWidget } from "./ProductsWidget";
import { ActionpadWidget } from "./ActionpadWidget";

export class ProductScreen extends ControlButtonsMixin(Component) {
    static template = "ProductScreen";
    static components = {
        ActionpadWidget,
        MobileOrderWidget,
        NumpadWidget,
        OrderWidget,
        ProductsWidget,
    };
    static numpadActionName = _lt("Payment");

    setup() {
        super.setup();
        this.pos = usePos();
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.notification = useService("pos_notification");
        this.numberBuffer = useService("number_buffer");
        onMounted(this.onMounted);

        useBarcodeReader({
            product: this._barcodeProductAction,
            weight: this._barcodeProductAction,
            price: this._barcodeProductAction,
            client: this._barcodePartnerAction,
            discount: this._barcodeDiscountAction,
        });

        this.state = useState({
            mobile_pane: this.props.mobile_pane || "right",
        });

        // Call `resset` when the `onMounted` callback in `numberBuffer.use` is done.
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
    /**
     * To be overridden by modules that checks availability of
     * connected scale.
     * @see _onScaleNotAvailable
     */
    get partner() {
        return this.currentOrder ? this.currentOrder.get_partner() : null;
    }
    get currentOrder() {
        return this.env.pos.get_order();
    }
    async updateSelectedOrderline({ buffer, key }) {
        if (this.env.pos.numpadMode === "quantity" && this.env.pos.disallowLineQuantityChange()) {
            const order = this.env.pos.get_order();
            if (!order.orderlines.length) {
                return;
            }
            const selectedLine = order.get_selected_orderline();
            const orderlines = order.orderlines;
            const lastId = orderlines.length !== 0 && orderlines.at(orderlines.length - 1).cid;
            const currentQuantity = this.env.pos
                .get_order()
                .get_selected_orderline()
                .get_quantity();

            if (selectedLine.noDecrease) {
                this.popup.add(ErrorPopup, {
                    title: this.env._t("Invalid action"),
                    body: this.env._t("You are not allowed to change this quantity"),
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
        } else {
            const val = buffer === null ? "remove" : buffer;
            this._setValue(val);
            if (val == "remove") {
                this.numberBuffer.reset();
                this.env.pos.numpadMode = "quantity";
            }
        }
    }
    _setValue(val) {
        if (this.currentOrder.get_selected_orderline()) {
            if (this.env.pos.numpadMode === "quantity") {
                const result = this.currentOrder.get_selected_orderline().set_quantity(val);
                if (!result) {
                    this.numberBuffer.reset();
                }
            } else if (this.env.pos.numpadMode === "discount") {
                this.currentOrder.get_selected_orderline().set_discount(val);
            } else if (this.env.pos.numpadMode === "price") {
                var selected_orderline = this.currentOrder.get_selected_orderline();
                selected_orderline.price_manually_set = true;
                selected_orderline.set_unit_price(val);
            }
        }
    }
    async _barcodeProductAction(code) {
        let product = this.env.pos.db.get_product_by_barcode(code.base_code);
        if (!product) {
            // find the barcode in the backend
            let foundProductIds = [];
            foundProductIds = await this.orm.search("product.product", [
                ["barcode", "=", code.base_code],
            ]);
            if (foundProductIds.length) {
                await this.env.pos._addProducts(foundProductIds);
                // assume that the result is unique.
                product = this.env.pos.db.get_product_by_id(foundProductIds[0]);
            } else {
                return this.popup.add(ErrorBarcodePopup, { code: code.base_code });
            }
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
                    price_manually_set: true,
                },
            });
        } else if (code.type === "weight") {
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
    _barcodePartnerAction(code) {
        const partner = this.env.pos.db.get_partner_by_barcode(code.code);
        if (partner) {
            if (this.currentOrder.get_partner() !== partner) {
                this.currentOrder.set_partner(partner);
                this.currentOrder.updatePricelist(partner);
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
    async _displayAllControlPopup() {
        await this.popup.add(ControlButtonPopup, {
            controlButtons: this.controlButtons,
        });
    }
    async _showDecreaseQuantityPopup() {
        this.numberBuffer.reset();
        const { confirmed, payload: inputNumber } = await this.popup.add(NumberPopup, {
            startingValue: 0,
            title: this.env._t("Set the new quantity"),
        });
        const newQuantity = inputNumber && inputNumber !== "" ? parseFloat(inputNumber) : null;
        if (confirmed && newQuantity !== null) {
            const order = this.env.pos.get_order();
            const selectedLine = this.env.pos.get_order().get_selected_orderline();
            const currentQuantity = selectedLine.get_quantity();
            if (newQuantity >= currentQuantity) {
                selectedLine.set_quantity(newQuantity);
                return;
            }
            if (newQuantity >= selectedLine.saved_quantity) {
                if (newQuantity == 0) {
                    order.remove_orderline(selectedLine);
                }
                selectedLine.set_quantity(newQuantity);
                return;
            }
            const newLine = selectedLine.clone();
            const decreasedQuantity = selectedLine.saved_quantity - newQuantity;
            newLine.order = order;
            newLine.set_quantity(-decreasedQuantity, true);
            selectedLine.set_quantity(selectedLine.saved_quantity);
            order.add_orderline(newLine);
        }
    }
    async onClickPay() {
        if (this.env.pos.get_order().server_id) {
            try {
                const isPaid = await this.orm.call("pos.order", "is_already_paid", [
                    this.env.pos.get_order().server_id,
                ]);
                if (isPaid) {
                    const searchDetails = {
                        fieldName: "RECEIPT_NUMBER",
                        searchTerm: this.env.pos.get_order().uid,
                    };
                    this.pos.showScreen("TicketScreen", {
                        ui: { filter: "SYNCED", searchDetails },
                    });
                    this.notification.add(this.env._t("The order has been already paid."), 3000);
                    this.env.pos.removeOrder(this.env.pos.get_order(), false);
                    this.env.pos.add_new_order();
                    return;
                }
            } catch (error) {
                if (!(error.message instanceof ConnectionLostError)) {
                    throw error;
                }
                // Reject error in a separate stack to display the offline popup, but continue the flow
                Promise.reject(error);
            }
        }
        if (
            this.env.pos
                .get_order()
                .orderlines.some(
                    (line) =>
                        line.get_product().tracking !== "none" && !line.has_valid_product_lot()
                ) &&
            (this.env.pos.picking_type.use_create_lots ||
                this.env.pos.picking_type.use_existing_lots)
        ) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: this.env._t("Some Serial/Lot Numbers are missing"),
                body: this.env._t(
                    "You are trying to sell products with serial/lot numbers, but some of them are not set.\nWould you like to proceed anyway?"
                ),
                confirmText: this.env._t("Yes"),
                cancelText: this.env._t("No"),
            });
            if (confirmed) {
                this.pos.showScreen("PaymentScreen");
            }
        } else {
            this.pos.showScreen("PaymentScreen");
        }
    }
    switchPane() {
        this.state.mobile_pane = this.state.mobile_pane === "left" ? "right" : "left";
    }
}

registry.category("pos_screens").add("ProductScreen", ProductScreen);
