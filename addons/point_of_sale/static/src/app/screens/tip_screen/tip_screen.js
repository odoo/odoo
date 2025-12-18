import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted } from "@odoo/owl";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";

export class TipScreen extends Component {
    static template = "point_of_sale.TipScreen";
    static props = {
        orderUuid: { type: String },
    };
    static components = {
        PriceFormatter,
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

    get tipAmount() {
        return this.env.utils.parseValidFloat(this.state.inputTipAmount) || 0;
    }

    get overallAmount() {
        return this.env.utils.formatCurrency(this.totalAmount + this.tipAmount);
    }

    get tipSubText() {
        if (this.state.selectedPercentage) {
            return _t("Includes a %s tip", this.state.selectedPercentage);
        }
        if (this.tipAmount > 0) {
            return _t("With %s tip Included", this.env.utils.formatCurrency(this.tipAmount));
        }
        return "";
    }

    get canSettle() {
        return Boolean(this.state.selectedPercentage || this.state.inputTipAmount);
    }

    get totalAmount() {
        return this._totalAmount;
    }
    get currentOrder() {
        return this.pos.getOrder();
    }
    get percentageTips() {
        return [
            { percentage: "15%", amount: 0.15 * this.totalAmount },
            { percentage: "20%", amount: 0.2 * this.totalAmount },
            { percentage: "25%", amount: 0.25 * this.totalAmount },
        ];
    }

    selectTip(tip = null) {
        this.state.selectedPercentage = tip?.percentage ?? null;
        this.state.inputTipAmount = tip?.percentage
            ? this.env.utils.formatCurrency(tip.amount, false)
            : "0";
    }

    async noTip() {
        this.selectTip();
        await this.validateTip();
    }

    async validateTip() {
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

        if (amount > this.pos.currency.round(0.25 * this.totalAmount)) {
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
        orderFinalized: true,
    },
});
