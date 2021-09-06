odoo.define('flexipharmacy.PaymentSummaryPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class PaymentSummaryPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ 
                StartDate: this.props.StartDate, 
                EndDate: this.props.EndDate,
                StartDateBlank:false, 
                EndDateBlank:false,
                PaymentSummaryMsg:"",
                PaymentSelectData: "sales_person",
                PaymentNumberReceipt: 1
            });
            this.start_date = useRef('payment_start_date');
        }
        onInputKeyDownNumberValidation(e) {
            if(e.which != 190 && e.which != 110 && e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57) && (e.which < 96 || e.which > 105) && (e.which < 37 || e.which > 40)) {
                e.preventDefault();
            }
        }
        getPayload() {
            return { 
                StartDate: this.state.StartDate,
                EndDate: this.state.EndDate,
                CurrentSession: this.state.CurrentReport,
                PaymentSelectData: this.state.PaymentSelectData,
                PaymentNumberReceipt: this.state.PaymentNumberReceipt
            };
        }
        PaymentSelectDataCheck(event){
            this.state.PaymentSelectData = event
        }
        CurrentSessionCheck(){
            this.state.CurrentSession = !this.state.CurrentSession
        }
        async confirm() {
            if (!this.state.CurrentReport){
                if (this.state.StartDate == ""){
                    this.state.StartDateBlank = true
                }else{
                    this.state.StartDateBlank = false
                }
                if (this.state.EndDate == ""){
                    this.state.EndDateBlank = true
                }else{
                    this.state.EndDateBlank = false
                }
                if (this.state.StartDateBlank || this.state.EndDateBlank){
                    return
                }
                if (this.state.StartDate > this.state.EndDate){
                    this.state.PaymentSummaryMsg = "Start date should not be greater than end date !"
                    return
                } else{
                    this.props.resolve({ confirmed: true, payload: await this.getPayload() });
                    this.trigger('close-popup');
                }
            } else{
                this.props.resolve({ confirmed: true, payload: await this.getPayload() });
                this.trigger('close-popup');
            }
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    PaymentSummaryPopup.template = 'PaymentSummaryPopup';
    PaymentSummaryPopup.defaultProps = {
        confirmText: 'Print',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(PaymentSummaryPopup);

    return PaymentSummaryPopup;
});
