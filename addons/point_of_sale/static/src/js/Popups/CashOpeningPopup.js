/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/pos_hook";
import { MoneyDetailsPopup } from "./MoneyDetailsPopup";
import { useState } from "@odoo/owl";

export class CashOpeningPopup extends AbstractAwaitablePopup {
    static template = "CashOpeningPopup";
    static defaultProps = { cancelKey: false };

    setup() {
        super.setup();
        this.manualInputCashCount = null;
        this.moneyDetails = null;
        this.pos = usePos();
        this.state = useState({
            notes: "",
            openingCash: this.pos.globalState.pos_session.cash_register_balance_start || 0,
        });
        this.popup = useService("popup");
        this.orm = useService("orm");
    }
    //@override
    async confirm() {
        this.pos.globalState.pos_session.cash_register_balance_start = this.state.openingCash;
        this.pos.globalState.pos_session.state = "opened";
        this.orm.call("pos.session", "set_cashbox_pos", [
            this.pos.globalState.pos_session.id,
            this.state.openingCash,
            this.state.notes,
        ]);
        super.confirm();
    }
    async openDetailsPopup() {
        const { confirmed, payload } = await this.popup.add(MoneyDetailsPopup, {
            moneyDetails: this.moneyDetails,
            total: this.manualInputCashCount ? 0 : this.state.openingCash,
        });
        if (confirmed) {
            const { total, moneyDetails, moneyDetailsNotes } = payload;
            this.state.openingCash = total;
            if (moneyDetailsNotes) {
                this.state.notes = moneyDetailsNotes;
            }
            this.manualInputCashCount = false;
            this.moneyDetails = moneyDetails;
        }
    }
    handleInputChange() {
        this.manualInputCashCount = true;
        this.moneyDetails = null;
        this.state.notes = "";
        if (typeof this.state.openingCash !== "number") {
            this.state.openingCash = 0;
        }
    }
}
