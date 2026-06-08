import { Dialog } from "@web/core/dialog/dialog";
import { Component, props, proxy, t } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { NumericInput } from "@point_of_sale/app/components/inputs/numeric_input/numeric_input";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MoneyDetailsPopup extends Component {
    static template = "point_of_sale.MoneyDetailsPopup";
    static components = { NumericInput, Dialog };
    props = props({
        moneyDetails: t.or([t.object(), t.literal(null)]).optional(null),
        action: t.string(),
        getPayload: t.function(),
        close: t.function(),
        context: t.string().optional(),
    });

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
        this.currency = this.pos.currency;
        this.state = proxy({
            moneyDetails: this.props.moneyDetails
                ? { ...this.props.moneyDetails }
                : Object.fromEntries(this.pos.models["pos.bill"].map((bill) => [bill.value, 0])),
        });
        this.env.dialogData.dismiss = () => {
            if (this.pos.canOpenCashdrawer) {
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
        let moneyDetailsNotes = !this.pos.currency.isZero(this.computeTotal())
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
