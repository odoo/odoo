/** @odoo-module */

import { Printer } from "@point_of_sale/js/printers";
import { is_email } from "web.utils";
import { useErrorHandlers } from "@point_of_sale/js/custom_hooks";
import Registries from "@point_of_sale/js/Registries";
import AbstractReceiptScreen from "@point_of_sale/js/Misc/AbstractReceiptScreen";

const { onMounted, useRef, status } = owl;

const ReceiptScreen = (AbstractReceiptScreen) => {
    class ReceiptScreen extends AbstractReceiptScreen {
        setup() {
            super.setup();
            useErrorHandlers();
            this.orderReceipt = useRef("order-receipt");
            const order = this.currentOrder;
            const partner = order.get_partner();
            this.orderUiState = order.uiState.ReceiptScreen;
            this.orderUiState.inputEmail =
                this.orderUiState.inputEmail || (partner && partner.email) || "";
            this.is_email = is_email;

            onMounted(() => {
                // Here, we send a task to the event loop that handles
                // the printing of the receipt when the component is mounted.
                // We are doing this because we want the receipt screen to be
                // displayed regardless of what happen to the handleAutoPrint
                // call.
                setTimeout(async () => {
                    if (status(this) === "mounted") {
                        const images = this.orderReceipt.el.getElementsByTagName("img");
                        for (const image of images) {
                            await image.decode();
                        }
                        await this.handleAutoPrint();
                    }
                }, 0);
            });
        }
        _addNewOrder() {
            this.env.pos.add_new_order();
        }
        async onSendEmail() {
            if (!is_email(this.orderUiState.inputEmail)) {
                this.orderUiState.emailSuccessful = false;
                this.orderUiState.emailNotice = this.env._t("Invalid email.");
                return;
            }
            try {
                await this._sendReceiptToCustomer();
                this.orderUiState.emailSuccessful = true;
                this.orderUiState.emailNotice = this.env._t("Email sent.");
            } catch {
                this.orderUiState.emailSuccessful = false;
                this.orderUiState.emailNotice = this.env._t(
                    "Sending email failed. Please try again."
                );
            }
        }
        get orderAmountPlusTip() {
            const order = this.currentOrder;
            const orderTotalAmount = order.get_total_with_tax();
            const tip_product_id =
                this.env.pos.config.tip_product_id && this.env.pos.config.tip_product_id[0];
            const tipLine = order
                .get_orderlines()
                .find((line) => tip_product_id && line.product.id === tip_product_id);
            const tipAmount = tipLine ? tipLine.get_all_prices().priceWithTax : 0;
            const orderAmountStr = this.env.pos.format_currency(orderTotalAmount - tipAmount);
            if (!tipAmount) {
                return orderAmountStr;
            }
            const tipAmountStr = this.env.pos.format_currency(tipAmount);
            return `${orderAmountStr} + ${tipAmountStr} tip`;
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get nextScreen() {
            return { name: "ProductScreen" };
        }
        whenClosing() {
            this.orderDone();
        }
        /**
         * This function is called outside the rendering call stack. This way,
         * we don't block the displaying of ReceiptScreen when it is mounted; additionally,
         * any error that can happen during the printing does not affect the rendering.
         */
        async handleAutoPrint() {
            if (this._shouldAutoPrint()) {
                await this.printReceipt();
                if (this.currentOrder._printed && this._shouldCloseImmediately()) {
                    this.whenClosing();
                }
            }
        }
        orderDone() {
            this.env.pos.removeOrder(this.currentOrder);
            this._addNewOrder();
            const { name, props } = this.nextScreen;
            this.showScreen(name, props);
            if (this.env.pos.config.iface_customer_facing_display) {
                this.env.pos.send_current_order_to_customer_facing_display();
            }
        }
        async printReceipt() {
            const isPrinted = await this._printReceipt();
            if (isPrinted) {
                this.currentOrder._printed = true;
            }
        }
        _shouldAutoPrint() {
            return this.env.pos.config.iface_print_auto && !this.currentOrder._printed;
        }
        _shouldCloseImmediately() {
            var invoiced_finalized = this.currentOrder.is_to_invoice()
                ? this.currentOrder.finalized
                : true;
            return (
                this.env.proxy.printer &&
                this.env.pos.config.iface_print_skip_screen &&
                invoiced_finalized
            );
        }
        async _sendReceiptToCustomer() {
            const printer = new Printer(null, this.env.pos);
            const receiptString = this.orderReceipt.el.innerHTML;
            const ticketImage = await printer.htmlToImg(receiptString);
            const order = this.currentOrder;
            const partner = order.get_partner();
            const orderName = order.get_name();
            const orderPartner = {
                email: this.orderUiState.inputEmail,
                name: partner ? partner.name : this.orderUiState.inputEmail,
            };
            const order_server_id = this.env.pos.validated_orders_name_server_id_map[orderName];
            await this.rpc({
                model: "pos.order",
                method: "action_receipt_to_customer",
                args: [[order_server_id], orderName, orderPartner, ticketImage],
            });
        }
    }
    ReceiptScreen.template = "ReceiptScreen";
    return ReceiptScreen;
};

Registries.Component.addByExtending(ReceiptScreen, AbstractReceiptScreen);

export default ReceiptScreen;
