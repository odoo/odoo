odoo.define('payment_ogone.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');
    const _t = core._t;

    manageForm.include({
        init: function () {
            this._super.apply(this, arguments);
            this.isManageForm = true;
        }
    });

    const ogoneMixin = {

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Prepare the inline form of Ogone for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {undefined}
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            let ogoneForm = document.getElementById('o_payment_acquirer_inline_form_' + paymentOptionId);
            if (provider !== 'ogone' || flow === 'token') {
                ogoneForm.style.display = 'none';
                return this._super(...arguments);
            }
            // Display the form
            ogoneForm.style.display = 'revert';
            // Ogone payment is performed in the Iframe. The client decides if he wants to save his payment data in the
            // Ogone form. It also contains a "submit" button se we hide also the "Pay button" to avoid confusing the client.

            this._hideInputs();

            if (this.startedIframe) {
                // The iframe is already initialized, no need to restart it
                return this._super(...arguments);
            }
            this._setPaymentFlow('direct');
            // We need to setup the payment method to attach the iframe.
            const self = this;
            this._rpc({
                route: '/payment/ogone/payment_setup',
                params: {
                    'acquirer_id': paymentOptionId,
                    'partner_id': parseInt(this.txContext.partnerId),
                    'amount': this.txContext.amount ? parseFloat(this.txContext.amount) : undefined,
                    'currency_id': this.txContext.currencyId
                        ? parseInt(this.txContext.currencyId)
                        : undefined,
                    'payment_option_id': paymentOptionId,
                    'reference_prefix': this.txContext.referencePrefix,
                    'order_id': this.txContext.orderId ? parseInt(this.txContext.orderId) : undefined,
                    'flow': flow,
                    'access_token': this.txContext.accessToken,
                    'landing_route': this.txContext.landingRoute,
                    'init_tx_route': this.txContext.initTxRoute,
                    'validation_route': this.txContext.validationRoute,
                    'isValidation': this.isManageForm !== undefined ? this.isManageForm : false,
                },
            }).then(paymentMethodsResult => {
                let iframe = document.getElementById('ogone-iframe-container_' + paymentMethodsResult['acquirer_id']);
                iframe.firstElementChild.src = paymentMethodsResult['ogone_iframe_url'];
                self.startedIframe = true;
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("An error occured when displayed this payment form."),
                    error.message.data.message
                );
            });
        },

    };
    checkoutForm.include(ogoneMixin);
    manageForm.include(ogoneMixin);
});
