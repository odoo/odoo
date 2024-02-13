/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero } from "@web/core/utils/numbers";
import { NumericInput } from "@point_of_sale/app/generic_components/inputs/numeric_input/numeric_input";

export class MoneyDetailsPopup extends Component {
    static template = "point_of_sale.MoneyDetailsPopup";
    static components = { NumericInput, Dialog };
    static props = {
        moneyDetails: { type: Object, optional: true },
        action: String,
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        moneyDetails: null,
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.currency = this.pos.currency;
        this.state = useState({
            moneyDetails: this.props.moneyDetails
                ? { ...this.props.moneyDetails }
                : Object.fromEntries(this.pos.models["pos.bill"].map((bill) => [bill.value, 0])),
        });
        this.env.dialogData.dismiss = () => {
            if (
                this.pos.config.iface_cashdrawer &&
                this.pos.hardwareProxy.connectionInfo.status === "connected"
            ) {
                this.pos.logEmployeeMessage(this.props.action, "ACTION_CANCELLED");
            }
        };
    }
    computeTotal(moneyDetails = this.state.moneyDetails) {
        return Object.entries(moneyDetails).reduce((total, [value, inputQty]) => {
            const quantity = isNaN(inputQty) ? 0 : inputQty;
            return total + parseFloat(value) * quantity;
        }, 0);
    }
    confirm() {
        let moneyDetailsNotes = !floatIsZero(this.computeTotal(), this.currency.decimal_places)
            ? "Money details: \n"
            : null;
        this.pos.models["pos.bill"].forEach((bill) => {
            if (this.state.moneyDetails[bill.value]) {
                moneyDetailsNotes += `  - ${
                    this.state.moneyDetails[bill.value]
                } x ${this.env.utils.formatCurrency(bill.value)}\n`;
            }
        });
        this.props.getPayload({
            total: this.computeTotal(),
            moneyDetailsNotes,
            moneyDetails: { ...this.state.moneyDetails },
            action: this.props.action,
        });
        this.props.close();
    }
    _parseFloat(value) {
        return parseFloat(value);
    }
}
