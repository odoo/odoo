odoo.define('point_of_sale.EditListInput', function(require) {
    'use strict';

    const { useRef } = owl.hooks;
    const { PosComponent } = require('point_of_sale.PosComponent');

    class EditListInput extends PosComponent {
        static template = 'EditListInput';
        inputRef = useRef('input');
        mounted() {
            this.inputRef.el.focus();
        }
        onKeyup(event) {
            if (event.which === 13 && event.target.value.trim() !== '') {
                this.trigger('create-new-item');
            }
        }
    }

    return { EditListInput };
});
