odoo.define('point_of_sale.CashMovePopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');

    const { useRef, useState } = owl;

    class CashMovePopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.state = useState({
                inputType: '', // '' | 'in' | 'out'
                inputAmount: '',
                inputReason: '',
                inputHasError: false,
            });
            this.inputAmountRef = useRef('input-amount-ref');
        }
        confirm() {
            try {
                parse.float(this.state.inputAmount);
            } catch (_error) {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Invalid amount');
                return;
            }
            if (this.state.inputType == '') {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Select either Cash In or Cash Out before confirming.');
                return;
            }
            if (this.state.inputType === 'out' && this.state.inputAmount > 0) {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Insert a negative amount with the Cash Out option.');
                return;
            }
            if (this.state.inputType === 'in' && this.state.inputAmount < 0) {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Insert a positive amount with the Cash In option.');
                return;
            }
            if (this.state.inputAmount < 0) {
                this.state.inputAmount = this.state.inputAmount.substring(1);
            }
            return super.confirm();
        }
        _onAmountKeypress(event) {
            if (event.key === '-') {
                event.preventDefault();
                this.state.inputAmount = this.state.inputType === 'out' ? this.state.inputAmount.substring(1) : `-${this.state.inputAmount}`;
                this.state.inputType = this.state.inputType === 'out' ? 'in' : 'out';
            }
        }
        onClickButton(type) {
            let amount = this.state.inputAmount;
            if (type === 'in') {
                this.state.inputAmount = amount.charAt(0) === '-' ? amount.substring(1) : amount;
            } else {
                this.state.inputAmount = amount.charAt(0) === '-' ? amount : `-${amount}`;
            }
            this.state.inputType = type;
            this.state.inputHasError = false;
            this.inputAmountRef.el && this.inputAmountRef.el.focus();
        }
        getPayload() {
            return {
                amount: parse.float(this.state.inputAmount),
                reason: this.state.inputReason.trim(),
                type: this.state.inputType,
            };
        }
    }
    CashMovePopup.template = 'point_of_sale.CashMovePopup';
    CashMovePopup.defaultProps = {
        cancelText: _t('Cancel'),
        title: _t('Cash In/Out'),
    };

    Registries.Component.add(CashMovePopup);

    return CashMovePopup;
});
