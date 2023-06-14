odoo.define('point_of_sale.CashOpeningPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    const { parse } = require('web.field_utils');
    const { useState } = owl;

    class CashOpeningPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.manualInputCashCount = null;
            this.state = useState({
                notes: "",
                openingCash: this.env.pos.pos_session.cash_register_balance_start || 0,
                displayMoneyDetailsPopup: false,
                inputHasError: false,
            });
        }
        //@override
        async confirm() {
            try {
                this.state.openingCash = parse.float(this.state.openingCash);
            } catch (_error) {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Invalid amount');
                return;
            }
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
            this.state.openingCash = total;
            if (moneyDetailsNotes) {
                this.state.notes = moneyDetailsNotes;
            }
            this.manualInputCashCount = false;
            this.closeDetailsPopup();
        }
        handleInputChange(ev) {
            this.manualInputCashCount = true;
            this.state.notes = "";
            try {
                parse.float(this.state.openingCash);
                this.state.inputHasError = false;
            } catch (_error) {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Invalid amount');
                return;
            }
        }
    }

    CashOpeningPopup.template = 'CashOpeningPopup';
    CashOpeningPopup.defaultProps = { cancelKey: false };
    Registries.Component.add(CashOpeningPopup);

    return CashOpeningPopup;
});
