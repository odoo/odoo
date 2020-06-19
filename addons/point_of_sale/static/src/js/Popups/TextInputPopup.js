odoo.define('point_of_sale.TextInputPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    // formerly TextInputPopupWidget
    class TextInputPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ inputValue: this.props.startingValue });
            this.inputRef = useRef('input');
        }
        mounted() {
            this.inputRef.el.focus();
        }
        getPayload() {
            return this.state.inputValue;
        }
    }
    TextInputPopup.template = 'TextInputPopup';
    TextInputPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: '',
        body: '',
        startingValue: '',
    };

    Registries.Component.add(TextInputPopup);

    return TextInputPopup;
});
