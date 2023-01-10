/** @odoo-module */

import { paymentExpressCheckoutForm } from '@payment/js/express_checkout_form';
import { _processDemoPayment } from 'payment_demo.payment_demo_mixin';

paymentExpressCheckoutForm.include({

    /**
     * Simulate a feedback from a payment provider and redirect the customer to the status page.
     *
     * @override method from payment.express_checkout_form
     * @private
     * @param {object} providerData
     * @return {Promise}
     */
    async _prepareExpressCheckoutForm(providerData) {
        if (providerData.providerCode !== 'demo') {
            return this._super(...arguments); 
        } 
        
        const shippingInformationRequired = document.querySelector('[name="o_payment_express_checkout_form"]').dataset.shippingInfoRequired
        if (shippingInformationRequired){
            let countryList = document.querySelector('#o_demo_express_checkout_container_'+ providerData.providerId + ' #ec_country');
            const countries = await this._rpc({ route: '/payment/demo/country_list'});
                
            let option;
            for (var country in countries){
                option = document.createElement('option');
                option.text = countries[country];
                option.value = country;
                countryList.add(option);
            }
        }
    },

    _onClickPay: function (ev){ 
        let expressShippingAddress = {};
            

        const expressCheckoutRoute = document.querySelector('[name="o_payment_express_checkout_form"]').dataset.expressCheckoutRoute;
        const shippingInformationRequired = document.querySelector('[name="o_payment_express_checkout_form"]').dataset.shippingInfoRequired
        const providerId = ev.target.dataset.providerId;
        if (shippingInformationRequired){
        
            const demoName = document.querySelector('#o_demo_express_checkout_container_'+ providerId + ' #ec_name');
            const demoMail = document.querySelector('#o_demo_express_checkout_container_'+ providerId + ' #ec_mail');
            const demoAddress = document.querySelector('#o_demo_express_checkout_container_'+ providerId + ' #ec_address');
            const demoAddress2 = document.querySelector('#o_demo_express_checkout_container_'+ providerId + ' #ec_address');
            const demoZip = document.querySelector('#o_demo_express_checkout_container_'+ providerId + ' #ec_zip');
            const demoCity = document.querySelector('#o_demo_express_checkout_container_'+ providerId + ' #ec_city');
            const demoCountry = document.querySelector('#o_demo_express_checkout_container_'+ providerId + ' #ec_country');

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
                                        'email': demoMail.value,
                                        'street': demoAddress.value,
                                        'street2': demoAddress2.value,
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
        }).then(() =>{
            this._rpc({
                route: this.txContext.transactionRoute,
                params: this._prepareTransactionRouteParams(providerId),
            }).then((processingValues) => {
                _processDemoPayment(processingValues);
            });
        });

    },
});
