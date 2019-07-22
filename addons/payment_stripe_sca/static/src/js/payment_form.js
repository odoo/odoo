odoo.define('payment_stripe.payment_form', function (require) {
    "use strict";
    
var ajax = require('web.ajax');
var core = require('web.core');
var PaymentForm = require('website_payment.payment_form');

var _t = core._t;

PaymentForm.include({

    start: function () {
        var def = this._super.apply(this, arguments);
        this.loadJS_def = ajax.loadJS("https://js.stripe.com/v3/");
        return $.when(def, this.loadJS_def).then(this.updateNewPaymentDisplayStatus.bind(this));
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
    _createStripeToken: function (ev) {
        var self = this;
        var button = $(ev.target).find('*[type="submit"]')[0]
        this.disableButton(button);
        var acquirerForm = this.$('.acquirer[data-acquirer-id="'+this.acquirer_id+'"]');
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
        return ajax.rpc('/payment/stripe/s2s/create_setup_intent',  {'acquirer_id': this.acquirer_id})
        .then(function(intent_secret) {
            // need to convert between ES6 promises and jQuery 2 deferred \o/
            stripe.handleCardSetup(intent_secret, card)
            .then(function(result) {
                if (result.error) {
                    self.enableButton(button);
                } else {
                    _.extend(formData, {"payment_method": result.setupIntent.payment_method});
                    return ajax.rpc(formData.data_set, formData)
                    .then(function (result) {
                        var $form = self.$el.find('#wc-payment-form');
                        if ($form.length) {
                            $form.find('select option[value="-1"]').val(result.id);
                            $form.find('select').val(result.id);
                            // directly submiting form triggers submit event and it goes to infinite loop
                            var new_form = $form.clone();
                            new_form.addClass('hidden').appendTo('body');
                            new_form[0].submit();
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
            });
        });
    },
    /**
     * called when clicking a Stripe radio if configured for s2s flow; instanciates the card and bind it to the widget.
     *
     * @private
     * @param {DOMElement} checkedRadio
     */
    _bindStripeCard: function () {
        var acquirerForm = this.$('.acquirer[data-acquirer-id="'+this.acquirer_id+'"]');
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
    _getAcquirerData: function () {
        if (this.$('select[name="pm_acquirer_id"]').length) {
            this.provider = this.$('select[name="pm_acquirer_id"] :selected').attr('provider');
            this.acquirer_id = this.$('select[name="pm_acquirer_id"] :selected').val();
        } else {
            this.provider  = this.$('.acquirer').attr('provider');
            this.acquirer_id = this.$('.acquirer').data().acquirerId;
        }
    },
    /**
     * @override
     */
    updateNewPaymentDisplayStatus: function () {
        this._getAcquirerData();
        if (this.provider === 'stripe') {
            // always re-init stripe (in case of multiple acquirers for stripe, make sure the stripe instance is using the right key)
            this._unbindStripeCard();
            this._bindStripeCard();
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
        this._getAcquirerData();
        if (this.provider === 'stripe' && (!ev.currentTarget.dataset.type && !this.$el.find('select[name="pay_meth"]').length) || (this.$el.find('select[name="pay_meth"]').length && this.$el.find('select[name="pay_meth"] :selected').val() == "-1")) {
            return this._createStripeToken(ev);
        } else {
            return this._super.apply(this, arguments);
        }
    },
});
});
