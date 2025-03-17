import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { MoneyDetailsPopup } from "@point_of_sale/app/utils/money_details_popup/money_details_popup";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { parseFloat } from "@web/views/fields/parsers";
import { Dialog } from "@web/core/dialog/dialog";

class CustomDialog extends Dialog {
    onEscape() {}
}

export class OpeningControlPopup extends Component {
    static template = "point_of_sale.OpeningControlPopup";
    static components = { Input, Dialog: CustomDialog };
    static props = {
        close: Function,
    };

    setup() {
        this.moneyDetails = null;
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({
            notes: "",
            openingCash: this.env.utils.formatCurrency(
                this.pos.session.cash_register_balance_start || 0,
                false
            ),
        });
        this.hardwareProxy = useService("hardware_proxy");
        this.ui = useService("ui");
    }
    async confirm() {
        await this.pos.data.call(
            "pos.session",
            "set_opening_control",
            [this.pos.session.id, parseFloat(this.state.openingCash), this.state.notes],
            {},
            true
        );
        this.pos.session.state = "opened";
        this.props.close();
    }
    async openDetailsPopup() {
        const action = _t("Cash control - opening");
        this.hardwareProxy.openCashbox(action);
        this.dialog.add(MoneyDetailsPopup, {
            moneyDetails: this.moneyDetails,
            action: action,
            getPayload: (payload) => {
                if (payload) {
                    const { total, moneyDetails, moneyDetailsNotes } = payload;
                    this.state.openingCash = this.env.utils.formatCurrency(total, false);
                    if (moneyDetailsNotes) {
                        this.state.notes = moneyDetailsNotes;
                    }
                    this.moneyDetails = moneyDetails;
                }
            },
            context: "Opening",
        });
    }
    handleInputChange() {
        if (!this.env.utils.isValidFloat(this.state.openingCash)) {
            return;
        }
        this.state.notes = "";
    }
    get cashMethodCount() {
        return this.pos.config.payment_method_ids.filter((pm) => pm.is_cash_count).length;
    }
}
