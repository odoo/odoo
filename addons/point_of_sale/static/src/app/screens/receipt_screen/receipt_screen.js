import { _t } from "@web/core/l10n/translation";
import { useErrorHandlers, useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { registry } from "@web/core/registry";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { useState, Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { isValidEmail } from "@point_of_sale/utils";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";

export class ReceiptScreen extends Component {
    static template = "point_of_sale.ReceiptScreen";
    static components = { OrderReceipt };
    static props = {
        orderUuid: { type: String },
    };

    setup() {
        super.setup();
        this.pos = usePos();
        useRouterParamsChecker();
        useErrorHandlers();
        this.ui = useService("ui");
        this.renderer = useService("renderer");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        const partner = this.currentOrder.getPartner();
        const email = partner?.invoice_emails || partner?.email || "";
        this.state = useState({
            email: email,
            phone: partner?.phone || "",
        });
        this.sendReceipt = useTrackedAsync(this._sendReceiptToCustomer.bind(this));
        this.doFullPrint = useTrackedAsync(() =>
            this.pos.printReceipt({ order: this.currentOrder })
        );
        this.doBasicPrint = useTrackedAsync(() =>
            this.pos.printReceipt({ order: this.currentOrder, basic: true })
        );
    }
    actionSendReceiptOnEmail() {
        this.sendReceipt.call({
            action: "action_send_receipt",
            destination: this.state.email,
            name: "Email",
        });
    }
    get currentOrder() {
        return this.pos.models["pos.order"].getBy("uuid", this.props.orderUuid);
    }
    get orderAmountPlusTip() {
        const order = this.currentOrder;
        const orderTotalAmount = order.priceIncl;
        const tip_product_id = this.pos.config.tip_product_id?.id;
        const tipLine = order
            .getOrderlines()
            .find((line) => tip_product_id && line.product_id.id === tip_product_id);
        const tipAmount = tipLine ? tipLine.prices.total_included : 0;
        const orderAmountStr = this.env.utils.formatCurrency(orderTotalAmount - tipAmount);
        if (!tipAmount) {
            return orderAmountStr;
        }
        const tipAmountStr = this.env.utils.formatCurrency(tipAmount);
        return `${orderAmountStr} + ${tipAmountStr} tip`;
    }
    get ticketScreen() {
        return { name: "TicketScreen" };
    }
    get isValidEmail() {
        return isValidEmail(this.state.email);
    }
    get isValidPhone() {
        return this.state.phone && /^\+?[()\d\s-.]{8,18}$/.test(this.state.phone);
    }
    showPhoneInput() {
        return false;
    }

    generateTicketImage = async (basicReceipt = false) =>
        await this.renderer.toJpeg(
            OrderReceipt,
            {
                order: this.currentOrder,
                basic_receipt: basicReceipt,
            },
            { addClass: "pos-receipt-print p-3" }
        );
    async _sendReceiptToCustomer({ action, destination }) {
        const order = this.currentOrder;
        if (!order.isSynced) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Unsynced order"),
                body: _t(
                    "This order is not yet synced to server. Make sure it is synced then try again."
                ),
                showReloadButton: true,
            });
            return Promise.reject();
        }
        const fullTicketImage = await this.generateTicketImage();
        const basicTicketImage = this.pos.config.basic_receipt
            ? await this.generateTicketImage(true)
            : null;
        await this.pos.data.call("pos.order", action, [
            [order.id],
            destination,
            fullTicketImage,
            basicTicketImage,
        ]);
    }
}

registry.category("pos_pages").add("ReceiptScreen", {
    name: "ReceiptScreen",
    component: ReceiptScreen,
    route: `/pos/ui/${odoo.pos_config_id}/receipt/{string:orderUuid}`,
    params: {
        orderUuid: true,
        orderFinalized: true,
    },
});
