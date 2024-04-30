odoo.define('point_of_sale.CashOpeningPopup', function(require) {
    'use strict';

    const { useValidateCashInput } = require('point_of_sale.custom_hooks');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { parse } = require('web.field_utils');

    const { useState, useRef } = owl;

    class CashOpeningPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.manualInputCashCount = null;
            this.state = useState({
                notes: "",
                openingCash: this.env.pos.pos_session.cash_register_balance_start || 0,
                displayMoneyDetailsPopup: false,
            });
            useValidateCashInput("openingCashInput", this.env.pos.pos_session.cash_register_balance_start);
            this.openingCashInputRef = useRef('openingCashInput');
        }
        //@override
        async confirm() {
            this.env.pos.pos_session.cash_register_balance_start = this.state.openingCash;
            this.env.pos.pos_session.state = 'opened';
            this.rpc({
                   model: 'pos.session',
                    method: 'set_cashbox_pos',
                    args: [this.env.pos.pos_session.id, this.state.openingCash, this.state.notes],
            });
            super.confirm();
        }
        openDetailsPopup() {
            this.state.openingCash = 0;
            this.state.notes = "";
            this.state.displayMoneyDetailsPopup = true;
        }
        closeDetailsPopup() {
            this.state.displayMoneyDetailsPopup = false;
        }
        updateCashOpening({ total, moneyDetailsNotes }) {
            this.openingCashInputRef.el.value = this.env.pos.format_currency_no_symbol(total);
            this.state.openingCash = total;
            if (moneyDetailsNotes) {
                this.state.notes = moneyDetailsNotes;
            }
            this.manualInputCashCount = false;
            this.closeDetailsPopup();
        }
        handleInputChange(event) {
            if (event.target.classList.contains('invalid-cash-input')) return;
            this.manualInputCashCount = true;
            this.state.openingCash = parse.float(event.target.value);
        }
    }

    CashOpeningPopup.template = 'CashOpeningPopup';
    CashOpeningPopup.defaultProps = { cancelKey: false };
    Registries.Component.add(CashOpeningPopup);

    return CashOpeningPopup;
});
