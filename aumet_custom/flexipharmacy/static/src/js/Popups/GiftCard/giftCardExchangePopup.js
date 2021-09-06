odoo.define('flexipharmacy.giftCardExchangePopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;

    class giftCardExchangePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            if (this.env.pos.config.menual_card_number){
                this.state = useState({ NewCardNumber: '', blankNewCardNumber:false});
            }else{
                this.state = useState({ NewCardNumber: this.guidGenerator(), blankNewCardNumber:false});
            }
            this.NewCardNumber = useRef('NewCardNumber');
        }
        guidGenerator() {
            return (new Date().getUTCMilliseconds().toString() + new Date().getTime().toString());
        }
        CardNumberValidation(e) {
            if(e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57) && (e.which < 96 || e.which > 105) && (e.which < 37 || e.which > 40)){
                e.preventDefault();
            }
        }
        getPayload() {
            return {NewCardNumber:Number(this.state.NewCardNumber)};
        }
        async confirm() {
            if (this.state.NewCardNumber <= 0){
                this.state.blankNewCardNumber = true
            }else{
                this.state.blankNewCardNumber = false
            }
            if (this.state.blankNewCardNumber){
                return
            }else {
                this.props.resolve({ confirmed: true, payload: await this.getPayload() });
                this.trigger('close-popup');
            }
            return
        }         
        cancel() {
            this.trigger('close-popup');
        }
    }
    giftCardExchangePopup.template = 'giftCardExchangePopup';
    giftCardExchangePopup.defaultProps = {
        confirmText: 'Replace',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(giftCardExchangePopup);

    return giftCardExchangePopup;
});
