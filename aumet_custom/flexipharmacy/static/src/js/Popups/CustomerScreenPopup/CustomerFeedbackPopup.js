odoo.define('flexipharmacy.CustomerFeedbackPopup', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');


    class CustomerFeedbackPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            useListener('change-ratings',this._changeRatings)
            this.state = useState({'currentRating': 0,})
        }
        _changeRatings(event){
            this.state.currentRating = event.detail.value
        }
        getPayload(){
            return this.state.currentRating;
        }
    }
    CustomerFeedbackPopup.template = 'CustomerFeedbackPopup';
    Registries.Component.add(CustomerFeedbackPopup);

    return {
        CustomerFeedbackPopup,
    };
});
