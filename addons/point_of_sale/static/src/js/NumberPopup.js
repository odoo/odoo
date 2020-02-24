odoo.define('point_of_sale.NumberPopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');
    const { useNumberBuffer } = require('point_of_sale.custom_hooks');

    // formerly NumberPopupWidget
    class NumberPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.props.decimalSeparator = this.env._t.database.parameters.decimal_point;
            this.numberBuffer = useNumberBuffer({
                decimalPoint: this.env._t.database.parameters.decimal_point,
                nonKeyboardEvent: 'numpad-click-input',
            });
            if (typeof this.props.startingValue === 'number' && this.props.startingValue > 0) {
                this.numberBuffer.set(this.props.startingValue.toString());
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
    };

    Chrome.addComponents([NumberPopup]);

    return { NumberPopup };
});
