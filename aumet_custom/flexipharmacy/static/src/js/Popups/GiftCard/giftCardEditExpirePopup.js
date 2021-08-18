odoo.define('flexipharmacy.giftCardEditExpirePopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class giftCardEditExpirePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ GiftCardmsg: '', NewExpireDate: '', blankNewExpireDate:false});
            this.NewExpireDate = useRef('NewExpireDate');
        }
        getPayload() { 
            return {new_expire_date:this.state.NewExpireDate};
        }
        async confirm() {
            if (this.state.NewExpireDate == ""){
                this.state.blankNewExpireDate = true
            }else{
                this.state.blankNewExpireDate = false
            }
            if (this.state.blankNewExpireDate){
                return
            }
            if (this.state.NewExpireDate != "" && this.props.selectedCard.expire_date > this.state.NewExpireDate){
                this.state.GiftCardmsg = "Please Select Date after expire Date !"
                return
            } else {
                this.state.GiftCardmsg = "";
                this.props.resolve({ confirmed: true, payload: await this.getPayload() });
                this.trigger('close-popup');
            }
            return
          
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    giftCardEditExpirePopup.template = 'giftCardEditExpirePopup';
    giftCardEditExpirePopup.defaultProps = {
        confirmText: 'Extend',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(giftCardEditExpirePopup);

    return giftCardEditExpirePopup;
});
