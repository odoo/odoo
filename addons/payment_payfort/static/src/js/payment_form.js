odoo.define('payment_payfort.payment_form', function(require) {
'use strict';
/**
 * Payment form override. This override will handle the tokenization process if
 * Payfort is configured with the 'Payment from Odoo' payment flow.
 */

var ajax = require('web.ajax');
var core = require('web.core');
var PaymentForm = require('payment.payment_form');

var qweb = core.qweb;
var _t = core._t;

PaymentForm.include({
    /**
     * @override
     */
    payEvent: async function(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a stripe as s2s payment method
        if (
            $checkedRadio.length === 1 &&
            this.isNewPaymentRadio($checkedRadio) &&
            $checkedRadio.data('provider') === 'payfort'
        ) {
            return this.payfortMerchantPageRequest(ev, $checkedRadio);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * @override
     */
    addPmEvent: function(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a stripe as add payment method
        if (
            $checkedRadio.length === 1 &&
            this.isNewPaymentRadio($checkedRadio) &&
            $checkedRadio.data('provider') === 'payfort'
        ) {
            return this.payfortMerchantPageRequest(ev, $checkedRadio, true);
        } else {
            return this._super.apply(this, arguments);
        }
    },

    /**
     * Launch a tokenization process. This will open an iframe that will contain the response of
     * a POST form submission to Payfort - this response will display the tokenization form and will
     * return to the /payment/payfort/merchant_page_return controller; this controller will render a
     * widget that will check the result of the toknization process and launch a 3D-Secure authentication
     * mechanism if needed. Regardless of the need for a 3DS process, this iframe will ultimately dispatch
     * a custom event to its parent DOM element; this method will listen for the event to continue the processs
     * (payment + tokenization or simple tokenization) or display an error if the tokenization process failed.
     * @param {Event}} ev - DOM event (submission of the payment form)
     * @param {jQuery Element} $checkedRadio - jQuery element wrapping the checked radio button of the acquirer
     * @param {Boolean} addPmEvent - true if we are in a payment method registration flow (without payment), false
     *                               if a payment is taking place during this tokenization
     */
    payfortMerchantPageRequest: async function(
        ev,
        $checkedRadio,
        addPmEvent
    ) {
        // reset error display and disable button until we finish
        let button;
        if (ev.type === 'submit') {
            button = $(ev.target).find('*[type="submit"]')[0];
        } else {
            button = ev.target;
        }
        this.hideError();
        this.disableButton(button);
        // contact server to get POST data to send to Payfort for the tokenization
        const acquirerId = this.getAcquirerIdFromRadio($checkedRadio);
        const acquirerForm = this.$(
            '#o_payment_add_token_acq_' + acquirerId
        );
        const inputsForm = $('input', acquirerForm);
        if (this.options.partnerId === undefined) {
            console.warn(
                'payment_form: unset partner_id when adding new token; things could go wrong'
            );
        }

        const formData = this.getFormData(inputsForm);
        const [templates, payfortInfo] = await Promise.all([
            ajax.loadXML(
                '/payment_payfort/static/src/xml/payfort_templates.xml',
                qweb
            ),
            this._rpc({
                route: '/payment/payfort/merchant_page_values',
                params: {
                    acquirer_id: acquirerId,
                    partner_id: this.options.partnerId,
                },
            }),
        ]);
        // render modal & submit POST form to Payfort, display loader until the iframe is ready with the response
        const $modal = $(
            qweb.render('payfort.iframe', {
                url: payfortInfo.url,
                id: acquirerId,
                values: payfortInfo.values,
            })
        );
        $modal.appendTo($('body')).modal({
            keyboard: true,
        });
        $modal.on('hidden.bs.modal', () => {
            // ensure the modal gets removed from the dom upon hiding to avoid modals interactions
            this.enableButton(button);
            $modal.remove();
        });
        const $iframe = $modal.find(
            `iframe#oe_payfort_iframe_${acquirerId}`
        );
        $iframe.on('load', () => {
            $iframe.show();
            $modal.find('.loader').hide();
        });
        $modal.find(`form#oe_payfort_merchant_page_${acquirerId}`).submit();
        // wait until the iframe resolves to a token id (or rejects)
        const prom = new Promise(function(resolve, reject) {
            $iframe[0].addEventListener(
                'odoo.payfort.token.return',
                (ev) => {
                    ev.stopPropagation();
                    let pmId;
                    if (ev.detail.success) {
                        pmId = ev.detail.tokenId;
                    }
                    // leave a very short time for customer to see the result (a big icon
                    // will make it clear even if they can't read the message fast enough)
                    setTimeout(() => {
                        pmId ? resolve(pmId) : reject();
                        $modal.modal('hide');
                    }, 3000);
                }
            );
        });
        let pmId;
        // and now we wait...
        try {
            pmId = await prom;
        } catch (e) {
            this.displayError(
                _t('Unable to save card'),
                _t(
                    'We were unable to save your credit card. Try again or use another card.'
                )
            );
            $modal.modal('hide');
            this.enableButton(button);
            return;
        }
        // we have our token, let's procedd!
        if (addPmEvent) {
            if (formData.return_url) {
                window.location = formData.return_url;
            } else {
                window.location.reload();
            }
        } else {
            $checkedRadio.val(pmId);
            this.el.submit();
        }
    },
});
});
