import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted } from "@odoo/owl";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";

export class TipScreen extends Component {
    static template = "point_of_sale.TipScreen";
    static props = {
        orderUuid: { type: String },
        finalizeValidation: { type: Function, optional: true },
    };
    setup() {
        this.pos = usePos();
        this.posReceiptContainer = useRef("pos-receipt-container");
        this.dialog = useService("dialog");
        this.state = this.currentOrder.uiState.TipScreen;
        this._totalAmount = this.currentOrder.priceIncl;
        useRouterParamsChecker();

        this.adjustableTipLine = this.currentOrder.adjustableTipLine;
        if (!this.adjustableTipLine) {
            this.goNextScreen();
            return;
        }

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
        return this.pos.getOrder();
    }
    get tipPercentages() {
        const config = this.pos.config;
        return [config.tip_percentage_1, config.tip_percentage_2, config.tip_percentage_3];
    }
    get percentageTips() {
        return this.tipPercentages.map((tip) => {
            const tipAmount = (tip / 100) * this.totalAmount;
            return {
                percentage: `${tip}%`,
                amount: this.env.utils.formatCurrency(tipAmount),
                inputTipAmount: tipAmount,
            };
        });
    }
    async validateTip() {
        if (!this.pos.config.module_pos_restaurant) {
            await this.props.finalizeValidation();
        }
        const amount = this.env.utils.parseValidFloat(this.state.inputTipAmount);
        const order = this.pos.getOrder();
        const serverId = order.isSynced && order.id;

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
        const maxTipPercentage = Math.max(...this.tipPercentages);
        const maxTipAmount = (maxTipPercentage / 100) * this.totalAmount;
        if (amount > maxTipAmount) {
            const confirmed = await ask(this.dialog, {
                title: _t("Are you sure?"),
                body: _t(
                    "%s is more than %s% of the order's total amount. Are you sure of this tip amount?",
                    this.env.utils.formatCurrency(amount),
                    maxTipPercentage
                ),
            });
            if (!confirmed) {
                return;
            }
        }

        order.state = "draft";
        await this.pos.setTip(amount);
        order.state = "paid";
        await this.adjustableTipLine.adjustAmount(amount);

        const serializedTipLine = order.getSelectedOrderline().serializeForORM();
        order.getSelectedOrderline().delete();
        const serverTipLine = await this.pos.data.create("pos.order.line", [serializedTipLine]);
        await this.pos.data.write("pos.order", [serverId], {
            is_tipped: true,
            tip_amount: serverTipLine[0].priceIncl,
        });

        this.goNextScreen();
    }
    goNextScreen() {
        this.pos.navigate("FeedbackScreen", {
            orderUuid: this.pos.getOrder().uuid,
        });
    }
    goPreviousScreen() {
        if (this.pos.config.module_pos_restaurant) {
            this.pos.navigate("FloorScreen");
        } else {
            this.pos.navigate("PaymentScreen", {
                orderUuid: this.pos.getOrder().uuid,
            });
        }
    }
    async printTipReceipt() {
        const order = this.currentOrder;
        const selectedPaymentLine = order.getSelectedPaymentline() || order.payment_ids[0];
        const receipts = [selectedPaymentLine?.ticket, selectedPaymentLine?.cashier_receipt].filter(
            Boolean
        );
        for (let i = 0; i < receipts.length; i++) {
            await this.pos.ticketPrinter.printTipReceipt({ order, name: receipts[i] });
        }
    }
}

registry.category("pos_pages").add("TipScreen", {
    name: "TipScreen",
    component: TipScreen,
    route: `/pos/ui/${odoo.pos_config_id}/tipping/{string:orderUuid}`,
    params: {
        orderUuid: true,
        orderFinalized: odoo.is_restaurant || false,
    },
});
