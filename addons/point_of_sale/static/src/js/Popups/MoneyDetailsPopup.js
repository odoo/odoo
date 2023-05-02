/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { useState } from "@odoo/owl";
import { CurrencyAmount } from "../Misc/CurrencyAmount";
import { usePos } from "@point_of_sale/app/pos_hook";

export class MoneyDetailsPopup extends AbstractAwaitablePopup {
    static components = { CurrencyAmount };
    static template = "MoneyDetailsPopup";

    setup() {
        super.setup();
        this.pos = usePos();
        this.currency = this.pos.globalState.currency;
        this.state = useState({
            moneyDetails: this.props.moneyDetails
                ? { ...this.props.moneyDetails }
                : Object.fromEntries(this.pos.globalState.bills.map((bill) => [bill.value, 0])),
            total: this.props.total ? this.props.total : 0,
        });
    }
    get firstHalfMoneyDetails() {
        const moneyDetailsKeys = Object.keys(this.state.moneyDetails).sort((a, b) => a - b);
        return moneyDetailsKeys.slice(0, Math.ceil(moneyDetailsKeys.length / 2));
    }
    get lastHalfMoneyDetails() {
        const moneyDetailsKeys = Object.keys(this.state.moneyDetails).sort((a, b) => a - b);
        return moneyDetailsKeys.slice(
            Math.ceil(moneyDetailsKeys.length / 2),
            moneyDetailsKeys.length
        );
    }
    updateMoneyDetailsAmount() {
        const total = Object.entries(this.state.moneyDetails).reduce(
            (total, money) => total + money[0] * money[1],
            0
        );
        this.state.total = this.pos.globalState.round_decimals_currency(total);
    }
    //@override
    async getPayload() {
        let moneyDetailsNotes = this.state.total ? "Money details: \n" : null;
        this.pos.globalState.bills.forEach((bill) => {
            if (this.state.moneyDetails[bill.value]) {
                moneyDetailsNotes += `  - ${
                    this.state.moneyDetails[bill.value]
                } x ${this.env.utils.formatCurrency(bill.value)}\n`;
            }
        });
        return {
            total: this.state.total,
            moneyDetailsNotes,
            moneyDetails: { ...this.state.moneyDetails },
        };
    }
}
