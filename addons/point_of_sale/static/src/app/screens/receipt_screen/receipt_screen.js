/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useErrorHandlers } from "@point_of_sale/app/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { useRef, useState, Component, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class ReceiptScreen extends Component {
    static template = "point_of_sale.ReceiptScreen";
    static components = { OrderReceipt };
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        this.printer = useState(useService("printer"));
        useErrorHandlers();
        this.ui = useState(useService("ui"));
        this.renderer = useService("renderer");
        this.dialog = useService("dialog");
        this.buttonMailReceipt = useRef("order-mail-receipt-button");
        this.currentOrder = this.pos.get_order();
        const partner = this.currentOrder.get_partner();
        this.orderUiState = this.currentOrder.uiState.ReceiptScreen;
        this.orderUiState.inputEmail =
            this.orderUiState.inputEmail || (partner && partner.email) || "";

        onMounted(() => {
            const order = this.pos.get_order();
            this.pos.sendOrderInPreparation(order);
        });
    }
    _addNewOrder() {
        this.pos.add_new_order();
    }
    onSendEmail() {
        if (this.buttonMailReceipt.el.classList.contains("fa-spin")) {
            this.orderUiState.emailSuccessful = false;
            this.orderUiState.emailNotice = _t("Sending in progress.");
            return;
        }
        this.buttonMailReceipt.el.className = "fa fa-fw fa-spin fa-circle-o-notch";
        this.orderUiState.emailNotice = "";

        if (!this.isValidEmail()) {
            this.orderUiState.emailSuccessful = false;
            this.buttonMailReceipt.el.className = "fa fa-paper-plane";
            this.orderUiState.emailNotice = _t("Invalid email.");
            return;
        }

        // Delay to allow the user to see the wheel that informs that the mail will be sent
        setTimeout(async () => {
            try {
                await this._sendReceiptToCustomer();
                this.orderUiState.emailSuccessful = true;
                this.orderUiState.emailNotice = _t("Email sent.");
            } catch {
                this.orderUiState.emailSuccessful = false;
                this.orderUiState.emailNotice = _t("Sending email failed. Please try again.");
            }
            this.buttonMailReceipt.el.className = "fa fa-paper-plane";
        }, 1000);
    }
    isValidEmail() {
        // A basic check of whether the `inputEmail` is an email or not.
        return /^.+@.+$/.test(this.orderUiState.inputEmail);
    }
    get orderAmountPlusTip() {
        const order = this.currentOrder;
        const orderTotalAmount = order.get_total_with_tax();
        const tip_product_id = this.pos.config.tip_product_id?.id;
        const tipLine = order
            .get_orderlines()
            .find((line) => tip_product_id && line.product_id.id === tip_product_id);
        const tipAmount = tipLine ? tipLine.get_all_prices().priceWithTax : 0;
        const orderAmountStr = this.env.utils.formatCurrency(orderTotalAmount - tipAmount);
        if (!tipAmount) {
            return orderAmountStr;
        }
        const tipAmountStr = this.env.utils.formatCurrency(tipAmount);
        return `${orderAmountStr} + ${tipAmountStr} tip`;
    }
    get nextScreen() {
        return { name: "ProductScreen" };
    }
    get ticketScreen() {
        return { name: "TicketScreen" };
    }
    orderDone() {
        this.currentOrder.uiState.screen_data.value = "";
        this.currentOrder.uiState.locked = true;
        this._addNewOrder();
        const { name, props } = this.nextScreen;
        this.pos.showScreen(name, props);
    }
    resumeOrder() {
        this.currentOrder.uiState.screen_data.value = "";
        this.currentOrder.uiState.locked = true;
        this.pos.selectNextOrder();
        const { name, props } = this.ticketScreen;
        this.pos.showScreen(name, props);
    }
    isResumeVisible() {
        return this.pos.get_order_list().length > 1;
    }
    async _sendReceiptToCustomer() {
        const partner = this.currentOrder.get_partner();
        const orderPartner = {
            email: this.orderUiState.inputEmail,
            name: partner ? partner.name : this.orderUiState.inputEmail,
        };
        await this.sendToCustomer(orderPartner, "action_receipt_to_customer");
    }
    async sendToCustomer(orderPartner, methodName) {
        const ticketImage = await this.renderer.toJpeg(
            OrderReceipt,
            {
                data: this.pos.get_order().export_for_printing(),
                formatCurrency: this.env.utils.formatCurrency,
            },
            { addClass: "pos-receipt-print" }
        );
        const order = this.currentOrder;
        const orderName = order.display_name;
        const order_id = order.id;
        if (typeof order_id !== "number") {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Unsynced order"),
                body: _t(
                    "This order is not yet synced to server. Make sure it is synced then try again."
                ),
            });
            return Promise.reject();
        }
        await this.pos.data.call("pos.order", methodName, [
            [order_id],
            orderName,
            orderPartner,
            ticketImage,
        ]);
    }
}

registry.category("pos_screens").add("ReceiptScreen", ReceiptScreen);
