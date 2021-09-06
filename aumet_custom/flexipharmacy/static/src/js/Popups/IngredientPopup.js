odoo.define('flexipharmacy.IngredientPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class IngredientPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ ingredients: this.props.ingredients});
        }
        getPayload(){
            return this.state.ingredients;
        }
        cancel(){
            this.trigger('close-popup');
        }
    }
    IngredientPopup.template = 'IngredientPopup';

    IngredientPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(IngredientPopup);

    return IngredientPopup;
});
