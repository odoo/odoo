import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillUnmount, signal, useEffect, useProps, t } from "@odoo/owl";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import {
    TipSelector,
    confirmLargeTip,
} from "@point_of_sale/app/components/tip_selector/tip_selector";

export class TipScreen extends Component {
    static template = "point_of_sale.TipScreen";
    props = useProps({
        orderUuid: t.string(),
        finalizeValidation: t.function().optional(),
    });
    static components = { TipSelector };
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = this.currentOrder.uiState.TipScreen;
        this._totalAmount = this.currentOrder.priceIncl;

        useRouterParamsChecker(this.constructor.name);

        this.adjustableTipLine = this.currentOrder.adjustableTipLine;
        if (!this.adjustableTipLine) {
            this.goNextScreen();
            return;
        }

        this.displayConfirmation = signal(null);
        this.isSettling = signal(false);
        this.settlePromise = null;

        const stopListening = this.pos.customerDisplay.onAction("tip", (action) =>
            this.onCustomerDisplayAction(action)
        );

        useEffect(() => {
            this.pos.customerDisplay.send({ tipScreen: this.customerDisplayPayload });
        });

        onWillUnmount(() => {
            stopListening();
            this.resolveDisplayConfirmation(false);
            this.pos.customerDisplay.send({ tipScreen: false });
        });

        onMounted(async () => {
            await this.printTipReceipt();
        });
    }

    get customerDisplayPayload() {
        return {
            orderUuid: this.currentOrder.uuid,
            overallAmount: this.overallAmount,
            tipSubText: this.tipSubText,
            percentageTips: this.percentageTips.map(({ percentage, amount }) => ({
                percentage,
                amount,
            })),
            inputTipAmount: this.state.inputTipAmount,
            selectedPercentage: this.state.selectedPercentage,
            isSettling: this.isSettling(),
            confirmation: this.displayConfirmation(),
            currencySymbol: this.currentOrder.orderCurrency.symbol,
        };
    }

    async onCustomerDisplayAction({ orderUuid, action, percentage, amount }) {
        if (orderUuid !== this.currentOrder?.uuid) {
            return;
        }
        const isChange = action === "select" || action === "input";
        if (isChange && this.settlePromise && !this.displayConfirmation()) {
            return;
        }
        switch (action) {
            case "select": {
                const tip = this.percentageTips.find((tip) => tip.percentage === percentage);
                if (tip) {
                    this.selectTip(tip);
                }
                break;
            }
            case "input":
                this.setCustomTip(amount);
                break;
            case "no_tip":
                await this.noTip({ fromDisplay: true });
                break;
            case "settle":
                if (this.settlePromise) {
                    break;
                }
                if (amount !== undefined) {
                    this.setCustomTip(amount);
                }
                if (this.canSettle) {
                    await this.settle({ fromDisplay: true });
                }
                break;
            case "confirm":
            case "cancel_confirm":
                this.resolveDisplayConfirmation(action === "confirm");
                break;
        }
    }

    onTipInput(value) {
        this.resolveDisplayConfirmation(false);
        this.state.inputTipAmount = value;
        this.state.selectedPercentage = null;
    }

    setCustomTip(amount) {
        const value = String(amount ?? "").trim();
        const parsed = Number(value);
        if (value && (!Number.isFinite(parsed) || parsed < 0)) {
            return;
        }
        this.resolveDisplayConfirmation(false);
        this.state.inputTipAmount = value;
        this.state.selectedPercentage = null;
    }

    async settle(options = {}) {
        if (this.settlePromise) {
            if (options.fromDisplay || !this.displayConfirmation()) {
                return;
            }
            this.resolveDisplayConfirmation(false);
            await this.settlePromise;
        }
        this.isSettling.set(true);
        this.settlePromise = this.validateTip(options);
        try {
            await this.settlePromise;
        } finally {
            this.settlePromise = null;
            this.isSettling.set(false);
        }
    }

    get tipAmount() {
        return this.pos.parseValidFloat(this.state.inputTipAmount) || 0;
    }

    resolveDisplayConfirmation(confirmed) {
        const resolve = this.pendingDisplayConfirmation;
        if (!resolve) {
            return;
        }
        this.pendingDisplayConfirmation = null;
        this.displayConfirmation.set(null);
        resolve(confirmed);
    }

    get overallAmount() {
        return this.pos.formatCurrency(this.totalAmount + this.tipAmount);
    }

    get tipSubText() {
        if (this.state.selectedPercentage) {
            return _t("Includes a %s tip", this.state.selectedPercentage);
        }
        if (this.tipAmount > 0) {
            return _t("With %s tip Included", this.pos.formatCurrency(this.tipAmount));
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
    get tipPercentages() {
        const config = this.pos.config;
        return [config.tip_percentage_1, config.tip_percentage_2, config.tip_percentage_3];
    }
    get percentageTips() {
        return this.tipPercentages.map((tip) => {
            const tipAmount = (tip / 100) * this.totalAmount;
            return {
                percentage: `${tip}%`,
                amount: this.pos.formatCurrency(tipAmount),
                inputTipAmount: tipAmount,
            };
        });
    }

    selectTip(tip = null) {
        this.resolveDisplayConfirmation(false);
        this.state.selectedPercentage = tip?.percentage ?? null;
        this.state.inputTipAmount = tip?.percentage
            ? this.pos.formatCurrency(tip.inputTipAmount, false)
            : "0";
    }

    async noTip(options = {}) {
        if (this.settlePromise) {
            if (options.fromDisplay || !this.displayConfirmation()) {
                return;
            }
            this.resolveDisplayConfirmation(false);
            await this.settlePromise;
        }
        this.selectTip();
        await this.settle(options);
    }

    async validateTip(options = {}) {
        if (!this.pos.config.module_pos_restaurant) {
            await this.props?.finalizeValidation?.();
        }
        const amount = this.pos.parseValidFloat(this.state.inputTipAmount);
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
            const params = {
                amount: this.pos.formatCurrency(amount),
                maxPercentage: maxTipPercentage,
            };
            let confirmed;
            if (options.fromDisplay) {
                confirmed = await new Promise((resolve) => {
                    this.pendingDisplayConfirmation = resolve;
                    this.displayConfirmation.set(params);
                });
            } else {
                confirmed = await confirmLargeTip(this.dialog, params);
            }
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
        delete serializedTipLine["record_dependencies"];
        delete serializedTipLine["relations_uuid_mapping"];
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
