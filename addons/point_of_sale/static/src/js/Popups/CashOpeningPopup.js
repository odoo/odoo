odoo.define('point_of_sale.CashOpeningPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

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
            this.env.pos.pos_session.state = 'opened';
            this.rpc({
                   model: 'pos.session',
                    method: 'set_cashbox_pos',
                    args: [this.env.pos.pos_session.id, this.state.openingCash, this.state.notes],
            });
            super.confirm();
        }
        async openDetailsPopup() {
            const { confirmed, payload } = await this.showPopup('MoneyDetailsPopup', {
                moneyDetails: this.moneyDetails, total: this.manualInputCashCount ? 0 : this.state.openingCash });
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
        }
    }

    CashOpeningPopup.template = 'CashOpeningPopup';
    CashOpeningPopup.defaultProps = { cancelKey: false };
    Registries.Component.add(CashOpeningPopup);

    return CashOpeningPopup;
});
