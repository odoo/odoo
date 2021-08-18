odoo.define('flexipharmacy.ProductSummaryPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class ProductSummaryPopup extends AbstractAwaitablePopup {
        onInputKeyDownNumberValidation(e) {
            if(e.which != 190 && e.which != 110 && e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57) && (e.which < 96 || e.which > 105) && (e.which < 37 || e.which > 40)) {
                e.preventDefault();
            }
        }
        constructor(){
            super(...arguments);
            this.state = useState({ 
                StartDate: this.props.StartDate, 
                EndDate: this.props.EndDate,
                StartDateBlank:false, 
                ProductSummaryMsg:"",
                EndDateBlank:false, 
                ProdNumberReceipt: this.props.ProdNumberReceipt
            });
            this.start_date = useRef('start_date');
        }
        getPayload() {
            return {
                StartDate: this.state.StartDate,
                EndDate: this.state.EndDate,
                CurrentSession: this.state.CurrentSession,
                ProductSummary: this.state.ProductSummary,
                CategorySummary: this.state.CategorySummary,
                LocationSummary: this.state.LocationSummary,
                PaymentSummary: this.state.PaymentSummary,
                ProdNumberReceipt: this.state.ProdNumberReceipt,
            };
        }
        ProductSummaryCheck(){
            this.state.ProductSummary = !this.state.ProductSummary
        }
        CategorySummaryCheck(){
            this.state.CategorySummary = !this.state.CategorySummary
        }
        PaymentSummaryCheck(){
            this.state.PaymentSummary = !this.state.PaymentSummary
        }
        LocationSummaryCheck(){
            this.state.LocationSummary = !this.state.LocationSummary
        }
        CurrentSessionCheck(){
            this.state.CurrentSession = !this.state.CurrentSession
        }
        async confirm() {
            if(this.state.ProdNumberReceipt <= 0){
                 $('#no_of_summary').css('border','1px solid red');
                 return
            }
            if (!this.state.CurrentSession){
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
                    this.state.ProductSummaryMsg = "Start date should not be greater than end date !"
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
    ProductSummaryPopup.template = 'ProductSummaryPopup';
    ProductSummaryPopup.defaultProps = {
        confirmText: 'Print',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(ProductSummaryPopup);

    return ProductSummaryPopup;
});
