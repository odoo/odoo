odoo.define('point_of_sale.CashMovePopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');
    const { useValidateCashInput } = require('point_of_sale.custom_hooks');

    class CashMovePopup extends AbstractAwaitablePopup {
        setup() {
            this.state = owl.hooks.useState({
                inputType: '', // '' | 'in' | 'out'
                inputAmount: '',
                inputReason: '',
                inputHasError: false,
                parsedAmount: 0,
            });
            this.inputAmountRef = owl.hooks.useRef('input-amount-ref');
            useValidateCashInput('input-amount-ref');
        }
        confirm() {
            try {
                parse.float(this.state.inputAmount);
            } catch (error) {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Invalid amount');
                return;
            }
            if (this.state.inputType == '') {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Select either Cash In or Cash Out before confirming.');
                return;
            }
            return super.confirm();
        }
        onClickButton(type) {
            this.state.inputType = type;
            this.state.inputHasError = false;
            this.inputAmountRef.el && this.inputAmountRef.el.focus();
        }
        getPayload() {
            return {
                amount: this.state.parsedAmount,
                reason: this.state.inputReason.trim(),
                type: this.state.inputType,
            };
        }
        handleInputChange(event) {
            if (event.target.classList.contains('invalid-cash-input')) return;
            this.state.parsedAmount = parse.float(this.inputAmountRef.el.value);
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
