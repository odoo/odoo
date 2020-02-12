odoo.define('point_of_sale.TextInputPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const { popupsRegistry } = require('point_of_sale.popupsRegistry');
    const { InputPopup } = require('point_of_sale.AbstractPopups');

    // formerly TextInputPopupWidget
    class TextInputPopup extends InputPopup {
        constructor() {
            super(...arguments);
            this.state = useState({ inputValue: '' });
            this.inputRef = useRef('input');
        }
        mounted() {
            this.inputRef.el.focus();
        }
        async setupData() {
            await super.setupData(...arguments);
            this.data = this.state.inputValue;
        }
    }

    popupsRegistry.add(TextInputPopup);

    return { TextInputPopup };
});
