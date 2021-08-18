odoo.define('flexipharmacy.giftCardCreatePopupConform', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class giftCardCreatePopupConform extends AbstractAwaitablePopup {
        guidGenerator() {
            return (new Date().getUTCMilliseconds().toString() + new Date().getTime().toString());
        }
        constructor() {
            super(...arguments);
            this.state = useState({CardNumber:'00', SelectCustomer:'', ExpireDate:"", Amount:"00", SelectCardType:"",Paid:'false'});
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
        getConfirmPayload() {
            return {card_no: this.state.CardNumber, select_customer: this.state.SelectCustomer, text_expire_date: this.state.ExpireDate, text_amount: Number(this.state.Amount), SelectCardType: this.state.SelectCardType, Paid: this.state.Paid,
            };
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    giftCardCreatePopupConform.template = 'giftCardCreatePopupConform';
    giftCardCreatePopupConform.defaultProps = {
        confirmText: 'Create',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(giftCardCreatePopupConform);

    return giftCardCreatePopupConform;
});
