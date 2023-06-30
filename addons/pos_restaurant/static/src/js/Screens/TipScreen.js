/** @odoo-module */

import { parseFloat } from "@web/views/fields/parsers";
import { renderToElement } from "@web/core/utils/render";
import { registry } from "@web/core/registry";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted } from "@odoo/owl";

export class TipScreen extends Component {
    static template = "pos_restaurant.TipScreen";
    setup() {
        this.pos = usePos();
        this.posReceiptContainer = useRef("pos-receipt-container");
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.hardwareProxy = useService("hardware_proxy");
        this.state = this.currentOrder.uiState.TipScreen;
        this._totalAmount = this.currentOrder.get_total_with_tax();

        onMounted(() => {
            this.printTipReceipt();
        });
    }
    get overallAmountStr() {
        const tipAmount = parseFloat(this.state.inputTipAmount || "0");
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
        const amount = parseFloat(this.state.inputTipAmount) || 0;
        const order = this.pos.get_order();
        const serverId = this.pos.validated_orders_name_server_id_map[order.name];

        if (!serverId) {
            this.popup.add(ErrorPopup, {
                title: this.env._t("Unsynced order"),
                body: this.env._t(
                    "This order is not yet synced to server. Make sure it is synced then try again."
                ),
            });
            return;
        }

        if (!amount) {
            await this.orm.call("pos.order", "set_no_tip", [serverId]);
            this.goNextScreen();
            return;
        }

        if (amount > 0.25 * this.totalAmount) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: "Are you sure?",
                body: `${this.env.utils.formatCurrency(
                    amount
                )} is more than 25% of the order's total amount. Are you sure of this tip amount?`,
            });
            if (!confirmed) {
                return;
            }
        }

        // set the tip by temporarily allowing order modification
        order.finalized = false;
        order.set_tip(amount);
        order.finalized = true;

        const paymentline = this.pos.get_order().get_paymentlines()[0];
        if (paymentline.payment_method.payment_terminal) {
            paymentline.amount += amount;
            await paymentline.payment_method.payment_terminal.send_payment_adjust(paymentline.cid);
        }

        // set_tip calls add_product which sets the new line as the selected_orderline
        const tip_line = order.selected_orderline;
        await this.orm.call("pos.order", "set_tip", [serverId, tip_line.export_as_JSON()]);
        this.goNextScreen();
    }
    goNextScreen() {
        this.pos.removeOrder(this.currentOrder);
        if (!this.pos.config.module_pos_restaurant) {
            this.pos.add_new_order();
        }
        const { name, props } = this.nextScreen;
        this.pos.showScreen(name, props);
    }
    get nextScreen() {
        if (this.pos.config.module_pos_restaurant) {
            const table = this.pos.table;
            return { name: "FloorScreen", props: { floor: table ? table.floor : null } };
        } else {
            return { name: "ProductScreen" };
        }
    }
    async printTipReceipt() {
        const receipts = [
            this.currentOrder.selected_paymentline.ticket,
            this.currentOrder.selected_paymentline.cashier_receipt,
        ];

        for (let i = 0; i < receipts.length; i++) {
            const data = receipts[i];
            var receipt = renderToElement("pos_restaurant.TipReceipt", {
                receipt: this.currentOrder.getOrderReceiptEnv().receipt,
                data: data,
                total: this.env.utils.formatCurrency(this.totalAmount),
            });

            if (this.hardwareProxy.printer) {
                await this._printIoT(receipt);
            } else {
                await this._printWeb(receipt);
            }
        }
    }

    async _printIoT(receipt) {
        const printResult = await this.hardwareProxy.printer.printReceipt(receipt);
        if (!printResult.successful) {
            await this.popup.add(ErrorPopup, {
                title: printResult.message.title,
                body: printResult.message.body,
            });
        }
    }

    async _printWeb(receipt) {
        try {
            this.posReceiptContainer.el.innerHTML = receipt;
            window.print();
        } catch {
            await this.popup.add(ErrorPopup, {
                title: this.env._t("Printing is not supported on some browsers"),
                body: this.env._t(
                    "Printing is not supported on some browsers due to no default printing protocol " +
                        "is available. It is possible to print your tickets by making use of an IoT Box."
                ),
            });
        }
    }
}

registry.category("pos_screens").add("TipScreen", TipScreen);
