odoo.define('point_of_sale.CashOpeningPopup', function(require) {
    'use strict';

    const { useState, useRef} = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const PosComponent = require('point_of_sale.PosComponent');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');


    class CashOpeningPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.cashBoxValue = this.env.pos.bank_statement.balance_start || 0;;
            this.currency = this.env.pos.currency;
            this.state = useState({
                notes: "",
            });
            useListener('numpad-click-input', this._updateCashAmount);
            useListener('update-cash', this._updateCashAmount);
            this.inputRef = useRef('input');
            NumberBuffer.use({
                nonKeyboardInputEvent: 'numpad-click-input',
                triggerAtInput: 'update-cash',
                useWithBarcode: false,
            });
        }

        startSession() {
            this.env.pos.bank_statement.balance_start = parseFloat(this.cashBoxValue);
            this.env.pos.pos_session.state = 'opened';
            this.rpc({
                   model: 'pos.session',
                    method: 'set_cashbox_pos',
                    args: [this.env.pos.pos_session.id, parseFloat(this.cashBoxValue), this.state.notes],
                });
            this.trigger('close-popup');
        }

        sendInput(value) {
            this.trigger('numpad-click-input', { value });
        }

        async _updateCashAmount(event) {
            let value = event.detail.value ? event.detail.value : event.detail.key
            if(value !== "Backspace") {
                if(this.cashBoxValue === 0) {
                    this.cashBoxValue = value !== "."? value: this.cashBoxValue + value;
                } else {
                    this.cashBoxValue += value;
                }
            } else {
                if(this.cashBoxValue.length > 1) {
                    this.cashBoxValue = this.cashBoxValue.substring(0, this.cashBoxValue.length -1)
                } else {
                    this.cashBoxValue = 0;
                }
            }
            this.render();
        }
    }

    CashOpeningPopup.template = 'CashOpeningPopup';
    Registries.Component.add(CashOpeningPopup);

    return CashOpeningPopup;
});
