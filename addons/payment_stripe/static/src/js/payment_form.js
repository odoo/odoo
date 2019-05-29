odoo.define('payment_stripe.payment_form', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var PaymentForm = require('payment.payment_form');

var qweb = core.qweb;
var _t = core._t;

ajax.loadXML('/payment_stripe/static/src/xml/stripe_templates.xml', qweb);

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
    _createStripeToken: function (ev, $checkedRadio, addPmEvent) {
        var self = this;
        var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
        var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
        var inputsForm = $('input', acquirerForm);
        if (this.options.partnerId === undefined) {
            console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
        }

        ajax.loadJS("https://js.stripe.com/v3/").then(function () {
            var formData = self.getFormData(inputsForm);
            var stripe = Stripe(formData.stripe_publishable_key);
            var element = stripe.elements();
            var card = element.create('card', {hidePostalCode: true});
            var dialog = new Dialog(self, {
                title: _t('Card Details'),
                size: 'medium',
                technical: false,
                buttons: [{text: _t('Submit'), classes: 'btn-primary', click: function (ev) {
                    stripe.createPaymentMethod('card', card).then(function (result) {
                        if (result.error) {
                            // Inform the user if there was an error.
                            var errorElement = document.getElementById('card-errors');
                            errorElement.textContent = result.error.message;
                        } else {
                            ev.currentTarget.disabled = true;
                            _.extend(formData, result.paymentMethod);
                            // Send the token to server.
                            self._rpc({
                                route: formData.data_set,
                                params: formData
                            }).then (function (data) {
                                if (addPmEvent) {
                                    if (formData.return_url) {
                                        window.location = formData.return_url;
                                    } else {
                                        window.location.reload();
                                    }
                                } else {
                                    $checkedRadio.val(data.id);
                                    self.$el.submit();
                                }
                            }).guardedCatch(function (error) {
                                // if the rpc fails, pretty obvious
                                self.enableButton(ev.target);

                                self.displayError(
                                    _t('Server Error'),
                                    _t("We are not able to add your payment method at the moment.") +
                                        error.message.data.message
                                );
                            });
                        }
                    });
                }}],
                $content: $(qweb.render('stripe.payment.element')),
            });
            dialog.opened().then(function () {
                self.disableButton(ev.target);
                card.mount('#card-element');
                card.addEventListener('change', function (event) {
                    var displayError = document.getElementById('card-errors');
                    displayError.textContent = '';
                    if (event.error) {
                        displayError.textContent = event.error.message;
                    }
                });
            });
            dialog.on('closed', self, function () {
                self.enableButton(ev.target);
            });
            dialog.open();
        });
    },
    /**
     * @override
     */
    updateNewPaymentDisplayStatus: function () {
        var $checkedRadio = this.$('input[type="radio"]:checked');

        if ($checkedRadio.length !== 1) {
            return;
        }

        //  hide add token form for stripe
        if ($checkedRadio.data('provider') === 'stripe' && this.isNewPaymentRadio($checkedRadio)) {
            this.$('[id*="o_payment_add_token_acq_"]').addClass('d-none');
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

        // first we check that the user has selected a stripe as s2s payment method
        if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'stripe') {
            this._createStripeToken(ev, $checkedRadio);
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

        // first we check that the user has selected a stripe as add payment method
        if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'stripe') {
            this._createStripeToken(ev, $checkedRadio, true);
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
