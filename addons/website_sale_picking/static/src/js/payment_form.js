/** @odoo-module */

import publicWidget from '@web/legacy/js/public/public_widget';
import { _t } from "@web/core/l10n/translation";
import '@website_sale/js/website_sale_delivery';

publicWidget.registry.websiteSaleDelivery.include({
    start: function () {
        this.onsiteOptions = document.querySelectorAll(
            'input[name="o_payment_radio"][data-is-onsite="1"]'
        );
        if(this.onsiteOptions.length > 0){ // Falsy evaluation does not work with NodeList
            this.paymentOptions = document.querySelectorAll('input[name="o_payment_radio"]');

            this.warning = document.createElement('p');
            const boldMsg = document.createElement('b');
            boldMsg.innerText = _t("No suitable payment method could be found.");
            this.warning.innerText = _t(
                "If you believe that it is an error, please contact the website administrator."
            );
            boldMsg.classList.add('d-block');
            this.warning.prepend(boldMsg);
            this.warning.classList.add('alert-warning', 'p-3', 'm-1', 'd-none');

            this.paymentMethodsContainer = document.querySelector('#payment_method');
            this.paymentMethodsContainer.querySelector(
                '#o_payment_form_options'
            ).append(this.warning);
        }
        return this._super.apply(this, ...arguments);
    },

    /**
     * Hide or show a payment option.
     * @param radio - The radio element of the payment method.
     * @param enabled - Whether the payment method should be shown.
     * @private
     */
    _setEnablePaymentOption(radio, enabled) {
        const node = radio.closest('[name="o_payment_option"]');
        if (enabled) {
            node.classList.remove('d-none');
            node.classList.add('list-group-item');
        } else {
            node.classList.add('d-none');
            node.classList.remove('list-group-item');
            radio.checked = false;
        }
    },

    /**
     * Checks all payment options and hides them if it is an onsite payment option and the delivery is not onsite.
     * @param {Event} ev the triggered document event
     * @private
     * @override
     */
    _onCarrierClick: function (ev) {
        this._super(...arguments);

        if(this.onsiteOptions.length === 0){ // Falsy evaluation does not work with NodeList
            return;
        }

        this.warning.classList.add('d-none');

        const input = ev.currentTarget.querySelector('input');
        let atLeastOneOptionAvailable = false;
        // Jquery because the button does not behave nicely with vanilla dataset.
        let $payButton = $('button[name="o_payment_submit_button"]');
        for (let option of this.paymentOptions) {
            if (option.dataset.isOnsite && input.dataset.deliveryType !== 'onsite') {
                if (option.checked) { // The payment option was selected.
                    $payButton.attr('disabled', true); // Reset the submit button.
                }
                this._setEnablePaymentOption(option, false);
            } else{
                if(option.dataset.isOnsite){
                    this._setEnablePaymentOption(option, true);
                }
                atLeastOneOptionAvailable = true;
            }
        }

        let disabledReasons = $payButton.data('disabled_reasons') || {};
        disabledReasons.noOptionAvailableOnsite = false;

        if (!atLeastOneOptionAvailable) {
            this.warning.classList.remove('d-none');
            disabledReasons.noOptionAvailableOnsite = true;
        }
        $payButton.data('disabled_reasons', disabledReasons);
    }
});
