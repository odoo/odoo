// odoo.define('payment_ogone.connect', function (require) {
//     "use strict";
//     var ajax = require('web.ajax');
//     var connect = ajax.loadJS ("/payment_ogone/static/lib/connectsdknoEncrypt.js");
// });


odoo.define('payment_ogone.payment_form', function (require) {
    "use strict";
    
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var Widget = require('web.Widget');
    var PaymentForm = require('payment.payment_form');
    ajax.loadJS("/payment_ogone/static/lib/connectsdknoEncrypt.js");
       
    var qweb = core.qweb;
    var _t = core._t;
    // ajax.loadXML('/payment_ogone/static/src/xml/ogone_templates.xml', qweb);
    
    PaymentForm.include({
    
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
    
        /**
         * called when clicking on pay now or add payment event to create token for credit card/debit card.
         *
         * @private
         * @param {Event} ev
         * @param {DOMElement} checkedRadio
         * @param {Boolean} addPmEvent
         */
        _createOgoneToken: function (ev, $checkedRadio, addPmEvent) {
            var self = this;
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            if (this.options.partnerId === undefined) {
                console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
            }
            //console.log(acquirerID.val());
            //console.log(inputsForm);
            var formData = this.getFormData(inputsForm);
            console.log(formData);
            // console.log(connect);
            var ingenico_session = new connect(sessionDetails);
            var cardNumber  = formData.cc_number;
            var amount = 100; // todo get with rpc ?
            var countryCode = 'BE'; // todo get with rpc ?

            var paymentDetails = {
                totalAmount: amount,
                countryCode: "BE",
                locale: "fr_BE",
                currency: "EUR",
                isRecurring: false
            };

            var sessionDetails = {
                assetUrl: "",
                clientApiUrl: "",
                clientSessionId: "",
                customerId: ""
            };

            var createPayload = function (ingenico_session, cardNumber, paymentDetails) {
                session.getIinDetails(cardNumber, paymentDetails).then(function (iinDetailsResponse) {
                    if (iinDetailsResponse.status !== "SUPPORTED") {
                        console.error("Card check error: " + iinDetailsResponse.status);
                        document.querySelector('.output').innerText = 'Something went wrong, check the console for more information.';
                        return;
                    }
                    session.getPaymentProduct(iinDetailsResponse.paymentProductId, paymentDetails).then(function (paymentProduct) {
                        var paymentRequest = session.getPaymentRequest();
                        paymentRequest.setPaymentProduct(paymentProduct);
                        paymentRequest.setValue("cardNumber", cardNumber);
                        paymentRequest.setValue("cvv", "123");
                        paymentRequest.setValue("expiryDate", "04/20");
            
                        if (!paymentRequest.isValid()) {
                            for (var error in paymentRequest.getErrorMessageIds()) {
                                console.error('error', error);
                            }
                        }
                        session.getEncryptor().encrypt(paymentRequest).then(function (paymentHash) {
                            document.querySelector('.output').innerText = 'Encrypted to: ' + paymentHash;
                        }, function (errors) {
                            console.error('Failed encrypting the payload, check your credentials');
                            document.querySelector('.output').innerText = 'Something went wrong, check the console for more information.';
                        });
            
                    }, function () {
                        console.error('Failed getting payment product, check your credentials');
                        document.querySelector('.output').innerText = 'Something went wrong, check the console for more information.';
                    });
            
                }, function () {
                    console.error('Failed getting IinDetails, check your credentials');
                    document.querySelector('.output').innerText = 'Something went wrong, check the console for more information.';
                });
            };
                        
            // var libUrl = "https://raw.githubusercontent.com/Ingenico-ePayments/connect-sdk-client-js/master/dist/connectsdk.noEncrypt.js" ;
            // ajax.loadJS (libUrl).then(function () {
            // var ingenico_session = new connect(sessionDetails);
            // createPayload(ingenico_session, cardNumber, paymentDetails);
            // });
        },
        /**
         * @override
         */
        updateNewPaymentDisplayStatus: function () {
            var $checkedRadio = this.$('input[type="radio"]:checked');
            var acquirerId = this.getAcquirerIdFromRadio($checkedRadio);
            if ($checkedRadio.length !== 1) {
                return;
            }
    
            //  hide add token form for ogone
            if ($checkedRadio.data('provider') === 'ogone' && this.isNewPaymentRadio($checkedRadio)) {
                //this.$('[id*="o_payment_add_token_acq_"]');
                this.$('#o_payment_add_token_acq_' + acquirerId).removeClass('d-none');
            } else {
                this._super.apply(this, arguments);
            }
        },
    
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
    
        /**
         * @override
         */
        payEvent: function (ev) {
            ev.preventDefault();
            var $checkedRadio = this.$('input[type="radio"]:checked');
            // first we check that the user has selected a ogone as s2s payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'ogone') {
                this._createOgoneToken(ev, $checkedRadio);
            } else {
                this._super.apply(this, arguments);
            }
        },
        /**
         * @override
         */
        addPmEvent: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var $checkedRadio = this.$('input[type="radio"]:checked');
    
            // first we check that the user has selected a Ogone as add payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'ogone') {
                this._createOgoneToken(ev, $checkedRadio, true);
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
    //debugger;
    return PaymentForm;
    });
