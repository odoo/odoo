odoo.define('flexipharmacy.MoneyInOutPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class MoneyInOutPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ inputReason: '', inputAmount: '', MoneyType: 'money_in', AmountBlank:false, ReasonBlank:false});
            this.reason = useRef('reason');
            this.amount = useRef('amount');
        }
        AmountValidation(e) {
            if(e.which != 190 && e.which != 110 && e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57) && (e.which < 96 || e.which > 105) && (e.which < 37 || e.which > 40)) {
                e.preventDefault();
            }
        }
        mounted() {
            this.reason.el.focus();
        }
        MoneyTypeCheck(event){
            this.state.MoneyType = event
        }
        getPayload() {
            if(this.state.MoneyType == 'money_in'){
                return {reason:this.state.inputReason, type:this.state.MoneyType, amount:Number(this.state.inputAmount)};
            }
            if(this.state.MoneyType == 'money_out'){
                return {reason:this.state.inputReason, type:this.state.MoneyType, amount:-this.state.inputAmount};
           }
        }
        async confirm() {
            if (!this.state.inputAmount){
                this.state.AmountBlank = true
            }else{
                this.state.AmountBlank = false
            }
            if (!this.state.inputReason){
                this.state.ReasonBlank = true
            }else{
                this.state.ReasonBlank = false
            }
            if (this.state.inputReason && this.state.inputAmount){
                this.props.resolve({ confirmed: true, payload: await this.getPayload() });
            }
        }
    }
    MoneyInOutPopup.template = 'MoneyInOutPopup';
    MoneyInOutPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(MoneyInOutPopup);

    return MoneyInOutPopup;
});
