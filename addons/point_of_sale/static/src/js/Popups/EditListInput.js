odoo.define('point_of_sale.EditListInput', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    /**
     * props {
     *     createNewItem: callback,
     *     removeItem: callback,
     *     item: object,
     * }
     */
    class EditListInput extends PosComponent {
        onKeyup(event) {
            if (event.key === "Enter" && event.target.value.trim() !== '') {
                this.props.createNewItem();
            }
        }
        onInput(event) {
            this.props.onInputChange(this.props.item._id, event.target.value);
        }
    }
    EditListInput.template = 'EditListInput';

    Registries.Component.add(EditListInput);

    return EditListInput;
});
