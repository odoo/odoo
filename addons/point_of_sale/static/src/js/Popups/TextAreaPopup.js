odoo.define('point_of_sale.TextAreaPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const { Chrome } = require('point_of_sale.chrome');
    const { addComponents } = require('point_of_sale.PosComponent');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');
    const Registry = require('point_of_sale.ComponentsRegistry');

    // formerly TextAreaPopupWidget
    // IMPROVEMENT: This code is very similar to TextInputPopup.
    //      Combining them would reduce the code.
    class TextAreaPopup extends AbstractAwaitablePopup {
        static template = 'TextAreaPopup';
        constructor() {
            super(...arguments);
            this.state = useState({ inputValue: '' });
            this.inputRef = useRef('input');
        }
        mounted() {
            this.inputRef.el.focus();
        }
        getPayload() {
            return this.state.inputValue;
        }
    }
    TextAreaPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    addComponents(Chrome, [TextAreaPopup]);

    Registry.add('TextAreaPopup', TextAreaPopup);

    return { TextAreaPopup };
});
