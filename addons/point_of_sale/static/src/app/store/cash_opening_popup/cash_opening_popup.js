/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { MoneyDetailsPopup } from "@point_of_sale/app/utils/money_details_popup/money_details_popup";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { parseFloat } from "@web/views/fields/parsers";
import { Dialog } from "@web/core/dialog/dialog";

export class CashOpeningPopup extends Component {
    static template = "point_of_sale.CashOpeningPopup";
    static components = { Input, Dialog };
    static defaultProps = { cancelKey: false };

    setup() {
        this.moneyDetails = null;
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({
            notes: "",
            openingCash: this.env.utils.formatCurrency(
                this.pos.pos_session.cash_register_balance_start || 0,
                false
            ),
        });
        this.orm = useService("orm");
        this.hardwareProxy = useService("hardware_proxy");
    }
    confirm() {
        this.pos.pos_session.state = "opened";
        this.orm.call("pos.session", "set_cashbox_pos", [
            this.pos.pos_session.id,
            parseFloat(this.state.openingCash),
            this.state.notes,
        ]);
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
        });
    }
    handleInputChange() {
        if (!this.env.utils.isValidFloat(this.state.openingCash)) {
            return;
        }
        this.state.notes = "";
    }
}
