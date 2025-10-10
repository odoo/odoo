import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted } from "@odoo/owl";
import { TipReceipt } from "@pos_restaurant/app/tip_receipt/tip_receipt";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";

export class TipScreen extends Component {
    static template = "pos_restaurant.TipScreen";
    static props = {};
    setup() {
        this.pos = usePos();
        this.posReceiptContainer = useRef("pos-receipt-container");
        this.dialog = useService("dialog");
        this.printer = useService("printer");
        this.state = this.currentOrder.uiState.TipScreen;
        this._totalAmount = this.currentOrder.get_total_with_tax();

        onMounted(async () => {
            await this.printTipReceipt();
        });
    }
    get overallAmountStr() {
        const tipAmount = this.env.utils.parseValidFloat(this.state.inputTipAmount);
        const original = this.env.utils.formatCurrency(this.totalAmount);
        const tip = this.env.utils.formatCurrency(tipAmount);
        const overall = this.env.utils.formatCurrency(this.totalAmount + tipAmount);
        return `${original} + ${tip} tip = ${overall}`;
    }
    get totalAmount() {
        return this._totalAmount;
    }
    get currentOrder() {
        return this.pos.get_order();
    }
    get percentageTips() {
        return [
            { percentage: "15%", amount: 0.15 * this.totalAmount },
            { percentage: "20%", amount: 0.2 * this.totalAmount },
            { percentage: "25%", amount: 0.25 * this.totalAmount },
        ];
    }
    async validateTip() {
        const amount = this.env.utils.parseValidFloat(this.state.inputTipAmount);
        const order = this.pos.get_order();
        const serverId = typeof order.id === "number" && order.id;

        if (!serverId) {
            this.dialog.add(AlertDialog, {
                title: _t("Unsynced order"),
                body: _t(
                    "This order is not yet synced to server. Make sure it is synced then try again."
                ),
            });
            return;
        }

        if (!amount) {
            await this.pos.data.write("pos.order", [serverId], { is_tipped: true, tip_amount: 0 });
            this.goNextScreen();
            return;
        }

        if (amount > 0.25 * this.totalAmount) {
            const confirmed = await ask(this.dialog, {
                title: "Are you sure?",
                body: `${this.env.utils.formatCurrency(
                    amount
                )} is more than 25% of the order's total amount. Are you sure of this tip amount?`,
            });
            if (!confirmed) {
                return;
            }
        }

        order.state = "draft";
        await this.pos.set_tip(amount);
        order.state = "paid";

        const paymentline = this.pos.get_order().payment_ids[0];
        if (paymentline.payment_method_id.payment_terminal) {
            paymentline.amount += amount;
            await paymentline.payment_method_id.payment_terminal.send_payment_adjust(
                paymentline.uuid
            );
        }

        const serializedTipLine = order.get_selected_orderline().serialize({ orm: true });
        order.get_selected_orderline().delete();
        const serverTipLine = await this.pos.data.create("pos.order.line", [serializedTipLine]);
        await this.pos.data.write("pos.order", [serverId], {
            is_tipped: true,
            tip_amount: serverTipLine[0].price_subtotal_incl,
        });

        this.goNextScreen();
    }
    goNextScreen() {
        if (!this.pos.config.module_pos_restaurant) {
            this.pos.add_new_order();
        }
        const { name, props } = this.nextScreen;
        this.pos.showScreen(name, props);
    }
    get nextScreen() {
        return { name: "ReceiptScreen" };
    }
    async printTipReceipt() {
        const order = this.currentOrder;
        const selectedPaymentLine = order.get_selected_paymentline() || order.payment_ids[0];
        const receipts = [selectedPaymentLine?.ticket, selectedPaymentLine?.cashier_receipt].filter(
            Boolean
        );
        for (let i = 0; i < receipts.length; i++) {
            await this.printer.print(
                TipReceipt,
                {
                    headerData: this.pos.getReceiptHeaderData(order),
                    data: receipts[i] || {},
                    total: this.env.utils.formatCurrency(this.totalAmount),
                },
                { webPrintFallback: false }
            );
        }
    }
}

registry.category("pos_screens").add("TipScreen", TipScreen);
