odoo.define('point_of_sale.EditListInput', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class EditListInput extends PosComponent {
        onKeyup(event) {
            if (event.key === "Enter" && event.target.value.trim() !== '') {
                this.trigger('create-new-item');
            }
        }
    }
    EditListInput.template = 'EditListInput';

    Registries.Component.add(EditListInput);

    return EditListInput;
});
