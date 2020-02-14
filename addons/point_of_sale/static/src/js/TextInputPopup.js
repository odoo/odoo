odoo.define('point_of_sale.TextInputPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const { Chrome } = require('point_of_sale.chrome');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');

    // formerly TextInputPopupWidget
    class TextInputPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ inputValue: '' });
            this.inputRef = useRef('input');
        }
        mounted() {
            this.inputRef.el.focus();
        }
        async getPayload() {
            return this.state.inputValue;
        }
    }

    Chrome.addComponents([TextInputPopup]);

    return { TextInputPopup };
});
