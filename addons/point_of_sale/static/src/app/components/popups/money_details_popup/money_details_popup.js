import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero } from "@web/core/utils/numbers";
import { NumericInput } from "@point_of_sale/app/generic_components/inputs/numeric_input/numeric_input";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MoneyDetailsPopup extends Component {
    static template = "point_of_sale.MoneyDetailsPopup";
    static components = { NumericInput, Dialog };
    static props = {
        moneyDetails: { type: [Object, { value: null }], optional: true },
        action: String,
        getPayload: Function,
        close: Function,
        context: { type: String, optional: true },
    };
    static defaultProps = {
        moneyDetails: null,
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
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
            ? this.props.context + " details: \n"
            : null;
        this.pos.models["pos.bill"].forEach((bill) => {
            if (this.state.moneyDetails[bill.value]) {
                moneyDetailsNotes +=
                    "\t" +
                    `${this.state.moneyDetails[bill.value]} x ${this.env.utils.formatCurrency(
                        bill.value
                    )}\n`;
            }
        });
        if (moneyDetailsNotes) {
            moneyDetailsNotes += _t(
                "Total: %s",
                this.env.utils.formatCurrency(this.computeTotal())
            );
        }
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
