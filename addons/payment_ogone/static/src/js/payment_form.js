odoo.define('payment_ogone.payment_form', function (require) {
    "use strict";
    
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var Widget = require('web.Widget');
    var PaymentForm = require('payment.payment_form');
    var connect = require('payment_ogone.connectsdk.noEncrypt');
       
    var qweb = core.qweb;
    var _t = core._t;
    
    ajax.loadXML('/payment_ogone/static/src/xml/ogone_templates.xml', qweb);
    var DummyWidget = Widget.extend({
         jsDependencies: ['/payment_ogone/static/lib/connectsdk.noEncrypt.js'],

    });

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
            var dummy = new DummyWidget(this);
            console.log(formData);
            console.log(connect);
            var session = this.session;
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

            var createPayload = function (session, cardNumber, paymentDetails) {
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
            createPayload(session, cardNumber, paymentDetails);



        },
        /**
         * @override
         */
        updateNewPaymentDisplayStatus: function () {
            var $checkedRadio = this.$('input[type="radio"]:checked');
            if ($checkedRadio.length !== 1) {
                return;
            }
    
            //  hide add token form for ogone
            if ($checkedRadio.data('provider') === 'ogone' && this.isNewPaymentRadio($checkedRadio)) {
                this.$('[id*="o_payment_add_token_acq_"]');
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
