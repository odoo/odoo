/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";

const { useState } = owl;

class CashOpeningPopup extends AbstractAwaitablePopup {
    setup() {
        super.setup();
        this.manualInputCashCount = null;
        this.moneyDetails = null;
        this.state = useState({
            notes: "",
            openingCash: this.env.pos.pos_session.cash_register_balance_start || 0,
        });
    }
    //@override
    async confirm() {
        this.env.pos.pos_session.cash_register_balance_start = this.state.openingCash;
        this.env.pos.pos_session.state = "opened";
        this.rpc({
            model: "pos.session",
            method: "set_cashbox_pos",
            args: [this.env.pos.pos_session.id, this.state.openingCash, this.state.notes],
        });
        super.confirm();
    }
    async openDetailsPopup() {
        const { confirmed, payload } = await this.showPopup("MoneyDetailsPopup", {
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

CashOpeningPopup.template = "CashOpeningPopup";
CashOpeningPopup.defaultProps = { cancelKey: false };
Registries.Component.add(CashOpeningPopup);

export default CashOpeningPopup;
