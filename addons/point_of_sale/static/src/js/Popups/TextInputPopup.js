odoo.define('point_of_sale.TextInputPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const { addComponents } = require('point_of_sale.PosComponent');
    const { Chrome } = require('point_of_sale.chrome');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');
    const Registry = require('point_of_sale.ComponentsRegistry');

    // formerly TextInputPopupWidget
    class TextInputPopup extends AbstractAwaitablePopup {
        static template = 'TextInputPopup';
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
    TextInputPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    addComponents(Chrome, [TextInputPopup]);

    Registry.add('TextInputPopup', TextInputPopup);

    return { TextInputPopup };
});
