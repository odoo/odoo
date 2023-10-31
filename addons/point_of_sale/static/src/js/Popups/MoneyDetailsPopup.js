odoo.define('point_of_sale.MoneyDetailsPopup', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    /**
     * Even if this component has a "confirm and cancel"-like buttons, this should not be an AbstractAwaitablePopup.
     * We currently cannot show two popups at the same time, what we do is mount this component with its parent
     * and hide it with some css. The confirm button will just trigger an event to the parent.
     */
    class MoneyDetailsPopup extends PosComponent {
        constructor() {
            super(...arguments);
            this.currency = this.env.pos.currency;
            this.state = useState({
                moneyDetails: Object.fromEntries(this.env.pos.bills.map(bill => ([bill.value, 0]))),
                total: 0,
            });
        }
        get firstHalfMoneyDetails() {
            const moneyDetailsKeys = Object.keys(this.state.moneyDetails).sort((a, b) => a - b);
            return moneyDetailsKeys.slice(0, moneyDetailsKeys.length/2);
        }
        get lastHalfMoneyDetails() {
            const moneyDetailsKeys = Object.keys(this.state.moneyDetails).sort((a, b) => a - b);
            return moneyDetailsKeys.slice(moneyDetailsKeys.length/2, moneyDetailsKeys.length);
        }
        isClosed() {
            return this.el.classList.contains('invisible')
        }
        openPopup() {
            this.el.classList.remove('invisible');
        }
        updateMoneyDetailsAmount() {
            let total = Object.entries(this.state.moneyDetails).reduce((total, money) => total + money[0] * money[1], 0);
            this.state.total = this.env.pos.round_decimals_currency(total);
        }
        _closePopup() {
            this.el.classList.add('invisible');
        }
        confirm() {
            let moneyDetailsNotes = this.state.total  ? 'Money details: \n' : null;
            this.env.pos.bills.forEach(bill => {
                if (this.state.moneyDetails[bill.value]) {
                    moneyDetailsNotes += `  - ${this.state.moneyDetails[bill.value]} x ${this.env.pos.format_currency(bill.value)}\n`;
                }
            })
            const payload = { total: this.state.total, moneyDetailsNotes, moneyDetails: { ...this.state.moneyDetails }};
            this.trigger('money-details-validated', payload);
            this._closePopup();
        }
        reset() {
            for (let key in this.state.moneyDetails) { this.state.moneyDetails[key] = 0 }
            this.state.total = 0;
        }
        discard() {
            this.reset();
            this._closePopup();
        }
    }

    MoneyDetailsPopup.template = 'MoneyDetailsPopup';
    Registries.Component.add(MoneyDetailsPopup);

    return MoneyDetailsPopup;

});
