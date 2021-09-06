odoo.define('flexipharmacy.CustomerCreatePopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');


    class CustomerCreatePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.nameRef = useRef('name')
            this.myKeyboard = null;
            this.emailRef = useRef('email')
            this.phoneRef = useRef('phone')
            this.state = useState({customerData:{name:false, street:false, city:false, zip: false, phone: false,
                                                email: false, }, currentInput:false});
        }
        mounted(){
            this.myKeyboard = new Keyboard({
              onChange: input => this.onChange(input),
              onKeyPress: button => this.onKeyPress(button)
            });
        }
        onChange(input) {
            if(this.state.currentInput){
               this.state.customerData[this.state.currentInput.name] = input;
               this.state.currentInput.value = input;
            }
        }
        onKeyPress(button) {
            if(document.querySelector(":focus")){
                this.state.currentInput = document.querySelector(":focus");
                this.myKeyboard.setInput(this.state.currentInput.value);
            }
        }
        validateEmail(value){
            var emailPattern = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$/;
            return emailPattern.test(value);
        }
        captureChange(event){
            this.state.customerData[event.target.name] = event.target.value;
        }
        async confirm() {
            if(this.state.customerData['name'] == false){
                this.nameRef.el.focus();
            }else if(this.state.customerData['email'] == false){
                this.emailRef.el.focus();
            }else if(!this.validateEmail(this.state.customerData['email'])){
                this.emailRef.el.focus();
            }else if(this.state.customerData['phone'] == false){
                this.phoneRef.el.focus();
            }else{
                this.props.resolve({ confirmed: true, payload: await this.getPayload() });
                this.trigger('close-popup');
            }
        }
        getPayload(){
            return this.state.customerData;
        }
    }
    CustomerCreatePopup.template = 'CustomerCreatePopup';
    Registries.Component.add(CustomerCreatePopup);

    return {
        CustomerCreatePopup,
    };
});
