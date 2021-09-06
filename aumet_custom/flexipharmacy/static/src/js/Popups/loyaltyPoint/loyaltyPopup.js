odoo.define('flexipharmacy.loyaltyPopup', function(require) {
    'use strict';

    const { useState, useRef, Component} = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class loyaltyPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ LoyaltyPoints: 0.00, pointsAmount:0.0});
        }
        async onInputKeyDownNumberVlidation(e) {
            if(e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57) && (e.which < 96 || e.which > 105) && (e.which < 37 || e.which > 40)) {
                e.preventDefault();
            }
            if(e.which == 13){
                this.state.pointsAmount = this.state.LoyaltyPoints * this.props.amount_per_point;
            }
            if(e.which == 190){
                e.preventDefault();
            }
        }
        getPayload() {
            return {amount:this.state.LoyaltyPoints};
        }
        cancel() {
            this.trigger('close-popup');
        }
    }

    loyaltyPopup.template = 'loyaltyPopup';
    loyaltyPopup.defaultProps = {
        confirmText: 'Loyalty Points Redeem',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(loyaltyPopup);

    return loyaltyPopup;
});
