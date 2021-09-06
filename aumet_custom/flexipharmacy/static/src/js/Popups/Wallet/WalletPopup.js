odoo.define('flexipharmacy.WalletPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class WalletPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            if (this.props.defined_amount){
                this.state = useState({ WalletAmount: parseFloat(this.props.defined_amount).toFixed(2)});
            }else{
                this.state = useState({ WalletAmount: 0.00});
            }
            this.WalletAmount = useRef('WalletAmount');
        }
        onInputKeyDownNumberVlidation(e) {
            if(e.which != 190 && e.which != 110 && e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57) && (e.which < 96 || e.which > 105) && (e.which < 37 || e.which > 40)) {
                e.preventDefault();
            }
        }
        getPayload() {
            return {amount:this.state.WalletAmount};
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    WalletPopup.template = 'WalletPopup';
    WalletPopup.defaultProps = {
        confirmText: 'Add to Wallet',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(WalletPopup);

    return WalletPopup;
});
