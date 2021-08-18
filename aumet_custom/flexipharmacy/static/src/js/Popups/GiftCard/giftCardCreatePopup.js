odoo.define('flexipharmacy.giftCardCreatePopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class giftCardCreatePopup extends AbstractAwaitablePopup {
        guidGenerator() {
            return (new Date().getUTCMilliseconds().toString() + new Date().getTime().toString());
        }
        CardNumberValidation(e) {
            if(e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57) && (e.which < 96 || e.which > 105) && (e.which < 37 || e.which > 40)){
                e.preventDefault();
            }
        }
        AmountValidation(e) {
            if(e.which != 190 && e.which != 110 && e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57) && (e.which < 96 || e.which > 105) && (e.which < 37 || e.which > 40)){
                e.preventDefault();
            }
        }
        constructor() {
            super(...arguments);
            if (this.env.pos.config.menual_card_number){
                this.state = useState({CardNumber:'00', SelectCustomer:'', ExpireDate:"", Amount:"00", SelectCardType:"",Paid:''
                });
            }else{
                this.state = useState({CardNumber:this.guidGenerator(), SelectCustomer:'', ExpireDate:"", Amount:"00", SelectCardType:"",Paid:''});
            }
            this.card_no = useRef('CardNumber');
            this.select_customer = useRef('SelectCustomer');
            this.text_expire_date = useRef('ExpireDate');
            this.text_amount = useRef('Amount');
            this.SelectCardType = useRef('SelectCardType');
            this.Paid = useRef('Paid');
        }
        mounted() {
            this.select_customer;
        }
        getPayload() {
            this.state.SelectCustomer = $('option[value="'+$('#select_customer').val()+'"]').attr('id')
            return {card_no: this.state.CardNumber, customer_id: this.state.SelectCustomer, expire_date: this.state.ExpireDate, card_value: Number(this.state.Amount), card_type: this.state.SelectCardType,
            };
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    giftCardCreatePopup.template = 'giftCardCreatePopup';

    giftCardCreatePopup.defaultProps = {
        confirmText: 'Create',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(giftCardCreatePopup);

    return giftCardCreatePopup;
});
