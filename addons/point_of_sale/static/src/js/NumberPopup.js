odoo.define('point_of_sale.NumberPopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');
    const { useNumberBuffer } = require('point_of_sale.custom_hooks');

    // formerly NumberPopupWidget
    class NumberPopup extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {Boolean} props.isPassword Show password popup.
         */
        constructor() {
            super(...arguments);
            useNumberBuffer({ nonKeyboardEvent: 'numpad-click-input' });
            if (typeof this.props.startingValue === 'number' && this.props.startingValue > 0) {
                this.numberBuffer.set(this.props.startingValue.toString());
            }
        }
        get decimalSeparator() {
            return this.env._t.database.parameters.decimal_point;
        }
        get inputBuffer() {
            if (this.numberBuffer.state.buffer === null) {
                return '';
            }
            if (this.props.isPassword) {
                return this.numberBuffer.state.buffer.replace(/./g, '•');
            } else {
                return this.numberBuffer.state.buffer;
            }
        }
        sendInput(key) {
            this.trigger('numpad-click-input', { key });
        }
        getPayload() {
            return this.numberBuffer.get();
        }
    }
    NumberPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Confirm ?',
        body: '',
        cheap: false,
        startingValue: null,
        isPassword: false,
    };

    Chrome.addComponents([NumberPopup]);

    return { NumberPopup };
});
