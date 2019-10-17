odoo.define('payment_stripe_sca.payment_form', function (require) {
    "use strict";
    
var ajax = require('web.ajax');
var core = require('web.core');
var PaymentForm = require('website_payment.payment_form');

var _t = core._t;

PaymentForm.include({

    start: function () {
        var self = this;
        var sup = this._super.bind(self);
        return ajax.loadJS("https://js.stripe.com/v3/")
        .then(function() {
            return sup();
        }).then(function() {
            return self.updateNewPaymentDisplayStatus();
        });
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
    _createStripeToken: function (ev, acquirerID) {
        var self = this;
        var button = $(ev.target).find('*[type="submit"]')[0]
        this.disableButton(button);
        var acquirerForm = this.$('.acquirer[data-acquirer-id="'+acquirerID+'"]');
        var inputsForm = $('input', acquirerForm);
        var formData = self.getFormData(inputsForm);
        if (formData.partner_id === undefined) {
            console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
        }

        var stripe = this.stripe;
        var card = this.stripe_card_element;
        if (card._invalid) {
            return this.enableButton(button);;
        }
        return ajax.rpc('/payment/stripe/s2s/create_setup_intent',  {'acquirer_id': acquirerID})
        .then(function(intent_secret) {
            // need to convert between ES6 promises and jQuery 2 deferred \o/
            return $.Deferred(function(defer) {
                if (!intent_secret) {
                    return defer.reject();
                }
                stripe.handleCardSetup(intent_secret, card)
                    .then(function(result) {defer.resolve(result)})
            }).then(function(result) {
                if (result.error) {
                    self.enableButton(button);
                } else {
                    _.extend(formData, {"payment_method": result.setupIntent.payment_method});
                    return ajax.rpc(formData.data_set, formData)
                    .then(function (result) {
                        var $form = self.$el.find('#wc-payment-form');
                        if ($form.length) {
                            return self._chargeStripeToken(formData, result.id)
                        } else {
                            if (formData.return_url) {
                                window.location = formData.return_url;
                            } else {
                                window.location.reload();
                            }
                        }

                    }).fail(function (result, event) {
                        // if the rpc fails, pretty obvious
                        self.enableButton(button);
                        self.displayError(
                            _t('Unable to save card'),
                            _t("We are not able to add your payment method at the moment. ") +
                                result.error
                        );
                    });
                }
            }).fail(function (error) {
                console.log('coucou!');
                self.enableButton(button);
            });
        });
    },
    _chargeExistingToken: function(ev, pm_id) {
        var self = this;
        var button = $(ev.target).find('*[type="submit"]')[0]
        var formData = self.getFormData(this.$el);
        return this._chargeStripeToken(formData, pm_id)
        .fail(function (error) {
            // if the rpc fails, pretty obvious
            self.enableButton(button);
            self.displayError(
                _t('Unable to process payment'),
                _t("We are not able to process your payment at the moment. ") +
                    error.message.data.message
            );
        });;
    },
    _chargeStripeToken: function(formData, pm_id) {
        var json_params = _.extend({}, formData, {pm_id: pm_id})
        var final_redirect;
        return ajax.rpc(this._guessJsonRoute(),json_params)
        .then(function (result) {
            var tx_info = result.tx_info;
            final_redirect = result.redirect;
            if (tx_info.state === 'done') {
                window.location = final_redirect;
            } else if (tx_info.state === 'pending' && tx_info.stripe_payment_intent_secret) {
                var stripe = new Stripe(tx_info.stripe_publishable_key);
                return $.Deferred(function(defer) {
                    stripe.handleCardPayment(tx_info.stripe_payment_intent_secret).then(function (result) {defer.resolve(result)});
                });
            }
        }).then(function (result) {
            if (result.error) {
                return $.Deferred().reject({"message": {"data": { "message": result.error.message}}});
            } else {
                return ajax.rpc('/payment/stripe/s2s/process_payment_intent',_.extend({}, result.paymentIntent, {reference: result.paymentIntent.description}));
            }
        }).then(function (result) {
            window.location = final_redirect;
        });
    },
    _guessJsonRoute: function() {
        return this.$('form').attr('action').replace('payment', 'json_payment');
    },
    /**
     * called when clicking a Stripe radio if configured for s2s flow; instanciates the card and bind it to the widget.
     *
     * @private
     * @param {DOMElement} checkedRadio
     */
    _bindStripeCard: function (acquirerID) {
        var acquirerForm = this.$('.acquirer[data-acquirer-id="'+acquirerID+'"]');
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
    updateNewPaymentDisplayStatus: function (ev) {
        var uses_stripe;
        if (this.$('.acquirer[data-acquirer-id]').length === 1) {
            uses_stripe = this.$('input[name="stripe_publishable_key"]').length;
            var acquirer_id = this.$('.acquirer').data().acquirerId;
        } else if (this.$('select[name="pm_acquirer_id"]').length) {
            var acquirer_id = this.$('select[name="pm_acquirer_id"]').val();
            var acquirerForm = this.$('.acquirer[data-acquirer-id="'+acquirer_id+'"]');
            uses_stripe = acquirerForm.find('input[name="stripe_publishable_key"]').length;
        } else {
            var provider  = this.$('.acquirer').data().provider;
            var acquirer_id = this.$('.acquirer').data().acquirerId;
            uses_stripe = provider === 'stripe';
        }
        if (uses_stripe) {
            // always re-init stripe (in case of multiple acquirers for stripe, make sure the stripe instance is using the right key)
            this._unbindStripeCard();
            this._bindStripeCard(acquirer_id);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    onSubmit: function (ev) {
        ev.preventDefault();
        var uses_stripe;
        var self = this;
        var sup = this._super.bind(this);
        if (this.$('select[name="pm_acquirer_id"]').length) {
            // special case for website_contract
            var selected_existing_pm = this.$('select[name="pay_meth"]').val() && parseInt(this.$('select[name="pay_meth"]').val()) !== -1
            if (!selected_existing_pm) {
                // creating a new token
                var acquirer_id = $(ev.target).closest('*[data-acquirer-id]').data().acquirerId;
                var acquirerForm = this.$('.acquirer[data-acquirer-id="'+acquirer_id+'"]');
                uses_stripe = acquirerForm.find('input[name="stripe_publishable_key"]').length;
            } else {
                // we need to remotely check if that token uses stripe
                var pm_id = this.$('select[name="pay_meth"]').val();
                return ajax.rpc('/payment/stripe/token_uses_stripe', {pm_id: pm_id})
                .then(function (result) {
                    if (result) {
                        return self._chargeExistingToken(ev, pm_id);
                    } else {
                        return sup();
                    }
                })
            }
        } else {
            var provider  = this.$('.acquirer').attr('provider');
            var acquirer_id = this.$('.acquirer').data().acquirerId;
            var acquirerForm = this.$('.acquirer[data-acquirer-id="'+acquirer_id+'"]');
            uses_stripe = acquirerForm.find('input[name="stripe_publishable_key"]').length;
        }
        if (uses_stripe && !ev.currentTarget.dataset.type) {
            return this._createStripeToken(ev, acquirer_id);
        } else {
            return this._super.apply(this, arguments);
        }
    },

    createToken: function(ev, data, action_url) {
        var uses_stripe;
        var self = this;
        if (this.$('select[name="pm_acquirer_id"]').length) {
            // special case for website_contract
            var selected_existing_pm = parseInt(this.$('select[name="pay_meth"]').val()) !== -1
            if (!selected_existing_pm) {
                // creating a new token
                var acquirer_id = $(ev.target).closest('*[data-acquirer-id]').data().acquirerId;
                var acquirerForm = this.$('.acquirer[data-acquirer-id="'+acquirer_id+'"]');
                uses_stripe = acquirerForm.find('input[name="stripe_publishable_key"]').length;
            } else {
                // we need to remotely check if that token uses stripe
                var pm_id = this.$('select[name="pay_meth"]').val();
                return ajax.rpc('/payment/stripe/token_uses_stripe', {pm_id: pm_id})
                .then(function (result) {
                    if (result) {
                        return self._chargeExistingToken(ev, pm_id);
                    } else {
                        return self._super.apply(self, arguments);
                    }
                })
            }
        } else {
            var provider  = this.$('.acquirer').data().provider;
            var acquirer_id = this.$('.acquirer').data().acquirerId;
            uses_stripe = provider === 'stripe';
        }
        if (uses_stripe && !ev.currentTarget.dataset.type) {
            return this._createStripeToken(ev, acquirer_id);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    _isStripeAcquirer: function() {
        var acq_id = this.$el.data('acquirer_id');
        return ajax.jsonRpc('/payment/get_provider', 'call', {acquirer_id: acq_id}).then(function(result) {
            return result === 'stripe';
        });
    },
    _redirectToStripeCheckout: function() {
        // Open Checkout with further options
        if ($.blockUI) {
            var msg = _t("Just one more second, we are redirecting you to Stripe...");
            $.blockUI({
                'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
            });
        }
        var button = this.$el.find('button#pay_stripe');
        this.disableButton(button);
        var stripe = Stripe($("input[name='stripe_key']").val());
    
        stripe.redirectToCheckout({
            sessionId: $("input[name='session_id']").val()
        }).then(function (result) {
            if (result.error) {
                displayError(result.error.message);
            }
        });
    },
});
});
