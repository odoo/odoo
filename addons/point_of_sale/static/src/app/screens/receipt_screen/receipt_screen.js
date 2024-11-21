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
        this.doFullPrint = useTrackedAsync(() => this.pos.printReceipt());
        this.doBasicPrint = useTrackedAsync(() => this.pos.printReceipt({ basic: true }));
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
        this.sendReceipt.call({
            action: "action_send_receipt",
            destination: this.state.email,
            name: "Email",
        });
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
    get isValidEmail() {
        return this.state.email && /^.+@.+$/.test(this.state.email);
    }
    get isValidPhone() {
        return this.state.phone && /^\+?[()\d\s-.]{8,18}$/.test(this.state.phone);
    }
    showPhoneInput() {
        return false;
    }
    orderDone() {
        this.currentOrder.uiState.screen_data.value = "";
        this.currentOrder.uiState.locked = true;
        this._addNewOrder();
        this.pos.searchProductWord = "";
        const { name, props } = this.nextScreen;
        this.pos.showScreen(name, props);
    }

    generateTicketImage = async (isBasicReceipt = false) =>
        await this.renderer.toJpeg(
            OrderReceipt,
            {
                data: this.pos.orderExportForPrinting(this.pos.get_order()),
                formatCurrency: this.env.utils.formatCurrency,
                basic_receipt: isBasicReceipt,
            },
            { addClass: "pos-receipt-print p-3" }
        );
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
        const fullTicketImage = await this.generateTicketImage();
        const basicTicketImage = await this.generateTicketImage(true);
        await this.pos.data.call("pos.order", action, [
            [order.id],
            destination,
            fullTicketImage,
            this.pos.basic_receipt ? basicTicketImage : null,
        ]);
    }
}

registry.category("pos_screens").add("ReceiptScreen", ReceiptScreen);
