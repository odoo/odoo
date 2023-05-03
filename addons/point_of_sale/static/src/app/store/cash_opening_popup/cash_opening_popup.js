/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { MoneyDetailsPopup } from "@point_of_sale/app/utils/money_details_popup/money_details_popup";
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";
import { useValidateCashInput } from "@point_of_sale/app/utils/hooks";

export class CashOpeningPopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.CashOpeningPopup";
    static defaultProps = { cancelKey: false };

    setup() {
        super.setup();
        this.manualInputCashCount = null;
        this.moneyDetails = null;
        this.pos = usePos();
        this.state = useState({
            notes: "",
            openingCash: this.pos.pos_session.cash_register_balance_start || 0,
        });
        this.popup = useService("popup");
        this.orm = useService("orm");
        useAutofocus({ refName: "cash-input" });
        this.hardwareProxy = useService("hardware_proxy");
        useValidateCashInput("cash-input", this.pos.pos_session.cash_register_balance_start);
    }
    //@override
    async confirm() {
        this.pos.pos_session.cash_register_balance_start = this.state.openingCash;
        this.pos.pos_session.state = "opened";
        this.orm.call("pos.session", "set_cashbox_pos", [
            this.pos.pos_session.id,
            this.state.openingCash,
            this.state.notes,
        ]);
        super.confirm();
    }
    async openDetailsPopup() {
        const action = _t("Cash control - opening");
        this.hardwareProxy.openCashbox(action);
        const { confirmed, payload } = await this.popup.add(MoneyDetailsPopup, {
            moneyDetails: this.moneyDetails,
            total: this.manualInputCashCount ? 0 : this.state.openingCash,
            action: action,
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
    handleInputChange(event) {
        if (event.target.classList.contains('invalid-cash-input')) return;
        this.manualInputCashCount = true;
        this.state.openingCash = parseFloat(event.target.value);
    }
}
