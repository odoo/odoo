odoo.define('point_of_sale.CashOpeningPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    const { useState } = owl;

    class CashOpeningPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.manualInputCashCount = null;
            this.state = useState({
                notes: "",
                openingCash: this.env.pos.bank_statement.balance_start || 0,
                displayMoneyDetailsPopup: false,
            });
        }
        //@override
        async confirm() {
            this.env.pos.bank_statement.balance_start = this.state.openingCash;
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
            this.state.openingCash = total;
            if (moneyDetailsNotes) {
                this.state.notes = moneyDetailsNotes;
            }
            this.manualInputCashCount = false;
            this.closeDetailsPopup();
        }
        handleInputChange() {
            this.manualInputCashCount = true;
            this.state.notes = "";
        }
    }

    CashOpeningPopup.template = 'CashOpeningPopup';
    CashOpeningPopup.defaultProps = { cancelKey: false };
    Registries.Component.add(CashOpeningPopup);

    return CashOpeningPopup;
});
