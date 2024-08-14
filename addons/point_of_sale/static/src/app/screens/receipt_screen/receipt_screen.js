import { _t } from "@web/core/l10n/translation";
import { useErrorHandlers, useTrackedAsync } from "@point_of_sale/app/utils/hooks";
import { registry } from "@web/core/registry";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { useState, Component, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class ReceiptScreen extends Component {
    static template = "point_of_sale.ReceiptScreen";
    static components = { OrderReceipt };
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        useErrorHandlers();
        this.ui = useState(useService("ui"));
        this.renderer = useService("renderer");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.currentOrder = this.pos.get_order();
        const partner = this.currentOrder.get_partner();
        this.state = useState({
            email: partner?.email || "",
            phone: partner?.mobile || "",
        });
        this.sendReceipt = useTrackedAsync(this._sendReceiptToCustomer.bind(this));
        this.doPrint = useTrackedAsync(() => this.pos.printReceipt());
        onMounted(() => {
            const order = this.pos.get_order();
            this.currentOrder.uiState.locked = true;
            this.pos.sendOrderInPreparation(order);
        });
    }

    _addNewOrder() {
        this.pos.add_new_order();
    }
    actionSendReceiptOnEmail() {
        if (this.isValidEmailAddress(this.state.email)) {
            this.sendReceipt.call({ action: "action_send_receipt", destination: this.state.email });
        } else {
            this.notification.add(_t("Please enter a valid email address"), {
                type: "danger",
            });
        }
    }
    get isValidEmail() {
        return this.isValidEmailAddress(this.state.email);
    }
    get isValidPhone() {
        return this.isValidPhoneNumber(this.state.phone);
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
        this.pos.resetProductScreenSearch();
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
        return this.pos.get_open_orders().length > 0;
    }
    async _sendReceiptToCustomer({ action, destination }) {
        const order = this.currentOrder;
        if (typeof order.id !== "number") {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Unsynced order"),
                body: _t(
                    "This order is not yet synced to server. Make sure it is synced then try again."
                ),
            });
            return Promise.reject();
        }
        const ticketImage = await this.renderer.toJpeg(
            OrderReceipt,
            {
                data: this.pos.orderExportForPrinting(this.pos.get_order()),
                formatCurrency: this.env.utils.formatCurrency,
            },
            { addClass: "pos-receipt-print" }
        );
        await this.pos.data.call("pos.order", action, [[order.id], destination, ticketImage]);
    }
    isValidEmailAddress(email) {
        return email && /^.+@.+$/.test(email);
    }
    isValidPhoneNumber(x) {
        return x && /^\+?[()\d\s-.]{8,18}$/.test(x);
    }
}

registry.category("pos_screens").add("ReceiptScreen", ReceiptScreen);
