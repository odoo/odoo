odoo.define('payment_demo.payment_form', require => {
    'use strict';

    const  DemoMixin = require('payment_demo.payment_demo_mixin');

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const paymentDemoForm = {

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Simulate a feedback from a payment provider and redirect the customer to the status page.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the provider
         * @param {number} providerId - The id of the provider handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {Promise}
         */
        _processDirectPayment: function (code, providerId, processingValues) {
            if (code !== 'demo') {
                return this._super(...arguments);
            }
            DemoMixin._processDemoPayment(processingValues);
        },

        /**
         * Prepare the inline form of Demo for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the selected payment option's provider
         * @param {integer} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: async function (code, paymentOptionId, flow) {
            if (code !== 'demo') {
                return this._super(...arguments);
            } else if (flow === 'token') {
                return Promise.resolve();
            }
            const demoExpressCheckoutForm = document.getElementById(`o_demo_express_checkout_container_${paymentOptionId}`);
            if (demoExpressCheckoutForm){ 
                const shippingInformationRequired = document.querySelector('[name="o_payment_express_checkout_form"]').dataset.shippingInfoRequired
                if (shippingInformationRequired){
                    let countryList = document.getElementById('ec_country');
                    const countries = await this._rpc({ route: '/payment/demo/country_list'});
                        
                    let option;
                    for (var country in countries){
                        option = document.createElement('option');
                        option.text = countries[country];
                        option.value = country;
                        countryList.add(option);
                    }
                }
            }
            this._setPaymentFlow('direct');
            return Promise.resolve()
        },
    };
    checkoutForm.include(paymentDemoForm);
    manageForm.include(paymentDemoForm);
});
