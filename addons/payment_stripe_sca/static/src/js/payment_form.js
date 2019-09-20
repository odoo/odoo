odoo.define('payment_stripe_sca.payment_form', function (require) {
    "use strict";
    
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var Dialog = require('web.Dialog');
    var PaymentForm = require('payment.payment_form');
    
    var _t = core._t;
    
    PaymentForm.include({
    
        willStart: function () {
            return this._super.apply(this, arguments).then(function () {
                return ajax.loadJS("https://js.stripe.com/v3/");
            })
        },
    
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
        _createStripeToken: function (ev, $checkedRadio, addPmEvent) {
            var self = this;
            var button = ev.target;
            this.disableButton(button);
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            if (this.options.partnerId === undefined) {
                console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
            }
    
            var formData = self.getFormData(inputsForm);
            var stripe = this.stripe;
            var card = this.stripe_card_element;
            if (card._invalid) {
                return this.enableButton(button);
            }
            return rpc.query({
                route: '/payment/stripe/s2s/create_setup_intent',
                params: {'acquirer_id': formData.acquirer_id}
            }).then(function(intent_secret){
                // need to convert between ES6 promises and jQuery 2 deferred \o/
                return $.Deferred(function(defer) {
                    stripe.handleCardSetup(intent_secret, card)
                        .then(function(result) {defer.resolve(result)})
                    });
            }).then(function(result) {
                if (result.error) {
                    return $.Deferred().reject({"message": {"data": { "message": result.error.message}}});
                } else {
                    _.extend(formData, {"payment_method": result.setupIntent.payment_method});
                    if (addPmEvent) {
                        // we force the check when adding a card trough here
                        formData.verify_validity = true;
                    }
                    return rpc.query({
                        route: formData.data_set,
                        params: formData,
                    })
                }
            }).then(function(result) {
                if (addPmEvent) {
                    if (formData.return_url) {
                        window.location = formData.return_url;
                    } else {
                        window.location.reload();
                    }
                } else {
                    return self._chargeStripeToken(formData, result.id);
                }
            }).fail(function (error, event) {
                // if the rpc fails, pretty obvious
                self.enableButton(button);
                self.displayError(
                    _t('Unable to process payment'),
                    _t("We are not able to process your payment at the moment. ") +
                        error.message.data.message
                );
            });
        },
        _chargeExistingToken: function(ev, $checkedRadio) {
            var pm_id = $checkedRadio.val();
            var self = this;
            var button = ev.target;
            this.disableButton(button);
            if (this.options.partnerId === undefined) {
                console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
            }
            var formData = self.getFormData(this.$el);
            return this._chargeStripeToken(formData, pm_id)
            .fail(function (error) {
                // if the rpc fails, pretty obvious
                self.enableButton(button);
                self.displayError(
                    _t('Unable to save card'),
                    _t("We are not able to add your payment method at the moment. ") +
                        error.message.data.message
                );
            });
        },
        _chargeStripeToken: function(formData, pm_id) {
            var json_params = _.extend({}, formData, {pm_id: pm_id})
            var final_redirect;
            return rpc.query({
                route: this._guessJsonRoute(),
                params: json_params,
            }).then(function (result) {
                var tx_info = result.tx_info;
                final_redirect = result.redirect;
                if (tx_info.state === 'done') {
                    window.location = final_redirect;
                } else if (tx_info.state === 'pending' && tx_info.stripe_payment_intent_secret) {
                    var stripe = new Stripe(tx_info.stripe_publishable_key);
                    return $.Deferred(function(defer) {
                        stripe.handleCardPayment(tx_info.stripe_payment_intent_secret).then(function (result) {defer.resolve(result)});
                    });
                } else {
                    return $.Deferred().reject({
                        "message": {"data": { "message": _t("An error occured with transaction ") + (tx_info.reference || "")}}
                    });
                }
            }).then(function (result) {
                if (result.error) {
                    return $.Deferred().reject({"message": {"data": { "message": result.error.message}}});
                } else {
                    return rpc.query({
                        route: '/payment/stripe/s2s/process_payment_intent',
                        params: _.extend({}, result.paymentIntent, {reference: result.paymentIntent.description}),
                    });
                }
            }).then(function (result) {
                window.location = final_redirect;
            });
        },
        /**
         * called when clicking a Stripe radio if configured for s2s flow; instanciates the card and bind it to the widget.
         *
         * @private
         * @param {DOMElement} checkedRadio
         */
        _bindStripeCard: function ($checkedRadio) {
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            var formData = this.getFormData(inputsForm);
            var stripe = Stripe(formData.stripe_publishable_key);
            var element = stripe.elements();
            var card = element.create('card', {hidePostalCode: true});
            card.mount('#card-element');
            card.on('ready', function(ev) {
                card.focus();
            });
            card.addEventListener('change', function (event) {
                var displayError = document.getElementById('card-errors');
                displayError.textContent = '';
                if (event.error) {
                    displayError.textContent = event.error.message;
                }
            });
            this.stripe = stripe;
            this.stripe_card_element = card;
        },
        /**
         * guess the json route to call for an interrupted payment flow
         * 
         * @private
         */
        _guessJsonRoute: function () {
            var route = this.$el.attr('action');
            var json_route = route.replace('token', 'json_token');
            if (json_route.indexOf('token') === -1) {
                // special case: subscription payment routes don't have 'token' in the url -_-
                json_route = route.replace('payment', 'json_payment');
            }
            return json_route;
        },
        /**
         * destroys the card element and any stripe instance linked to the widget.
         *
         * @private
         */
        _unbindStripeCard: function () {
            if (this.stripe_card_element) {
                this.stripe_card_element.destroy();
            }
            this.stripe = undefined;
            this.stripe_card_element = undefined;
        },
        /**
         * @override
         */
        updateNewPaymentDisplayStatus: function () {
            var $checkedRadio = this.$('input[type="radio"]:checked');
    
            if ($checkedRadio.length) {
                var provider = $checkedRadio.data('provider');
                if (provider === 'stripe') {
                    // always re-init stripe (in case of multiple acquirers for stripe, make sure the stripe instance is using the right key)
                    this._unbindStripeCard();
                    if (this.isNewPaymentRadio($checkedRadio)) {
                        this._bindStripeCard($checkedRadio);
                    }
                }
            }
            return this._super.apply(this, arguments);
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
    
            // first we check that the user has selected a stripe as s2s payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'stripe') {
                return this._createStripeToken(ev, $checkedRadio);
            } else if ($checkedRadio.attr('name') === 'pm_id' && !this.isNewPaymentRadio($checkedRadio) && !this.isFormPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'stripe') {
                return this._chargeExistingToken(ev, $checkedRadio);
            } else {
                return this._super.apply(this, arguments);
            }
        },
        /**
         * @override
         */
        addPmEvent: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var $checkedRadio = this.$('input[type="radio"]:checked');
    
            // first we check that the user has selected a stripe as add payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'stripe') {
                return this._createStripeToken(ev, $checkedRadio, true);
            } else {
                return this._super.apply(this, arguments);
            }
        },
    });
});
