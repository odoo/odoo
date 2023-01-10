odoo.define('payment_demo.payment_form', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const paymentDemoMixin = {

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

            const demoExpressCheckoutForm = document.getElementById(`o_demo_express_checkout_container_${providerId}`);
            const customerInput = document.getElementById('customer_input').value;
            const simulatedPaymentState = document.getElementById('simulated_payment_state').value;
            var expressShippingAddress = {};
            
            if (demoExpressCheckoutForm){ 
                const expressCheckoutRoute = document.querySelector('[name="o_payment_express_checkout_form"]').dataset.expressCheckoutRoute;
                const shippingInformationRequired = document.querySelector('[name="o_payment_express_checkout_form"]').dataset.shippingInfoRequired
                if (shippingInformationRequired){
                
                    const demoName = document.getElementById('ec_name');
                    const demoMail = document.getElementById('ec_mail').value;
                    const demoAddress = document.getElementById('ec_address');
                    const demoAddress2 = document.getElementById('ec_address2').value;
                    const demoZip = document.getElementById('ec_zip');
                    const demoCity = document.getElementById('ec_city');
                    const demoCountry = document.getElementById('ec_country');

                    if (
                        !demoAddress.reportValidity()
                        || !demoName.reportValidity()
                        || !demoZip.reportValidity()
                        || !demoCity.reportValidity()
                    ) {
                        this._enableButton();
                        $('body').unblock(); 
                        return Promise.resolve(); 
                    }

                    expressShippingAddress =  {'name': demoName.value,
                                                'email': demoMail,
                                                'street': demoAddress.value,
                                                'street2': demoAddress2,
                                                'country': demoCountry.value,
                                                'state':'',
                                                'city': demoCity.value,
                                                'zip':demoZip.value
                    }
                }   

                return this._rpc({
                    route: expressCheckoutRoute,
                    params: {
                        'shipping_address': expressShippingAddress,
                        'billing_address': {'name': 'Demo User',
                                            'email': 'demo@test.com',
                                            'street': 'Baker Street 21',
                                            'street2': '',
                                            'country': 'BE',
                                            'state':'',
                                            'zip':'5000'
                        },
                    }
                }).then(() => {
                    this._rpc({
                        route: '/payment/demo/simulate_payment',
                        params: {
                            'reference': processingValues.reference,
                            'payment_details': customerInput,
                            'simulated_state': simulatedPaymentState,
                        },
                    }).then(() => {
                        window.location = '/payment/status';
                    });
                });
            }

            return this._rpc({
                route: '/payment/demo/simulate_payment',
                params: {
                    'reference': processingValues.reference,
                    'payment_details': customerInput,
                    'simulated_state': simulatedPaymentState,
                },
            }).then(() => {
                window.location = '/payment/status';
            });
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
    checkoutForm.include(paymentDemoMixin);
    manageForm.include(paymentDemoMixin);
});
