/** @odoo-module */

import publicWidget from '@web/legacy/js/public/public_widget';
import { _t } from "@web/core/l10n/translation";
import '@website_sale/js/website_sale_delivery';

publicWidget.registry.websiteSaleDelivery.include({
    start: function () {
        this.codOptions = document.querySelectorAll(
            'input[name="o_payment_radio"][data-provider-custom-mode="cash_on_delivery"]'
        );
        if (this.codOptions.length > 0) { // Falsy evaluation does not work with NodeList
            this.paymentOptions = document.querySelectorAll('input[name="o_payment_radio"]');

            this.warning = document.createElement('p');
            const boldMsg = document.createElement('b');
            boldMsg.innerText = _t("No suitable payment method could be found.");
            this.warning.innerText = _t(
                "If you believe that it is an error, please contact the website administrator."
            );
            boldMsg.classList.add('d-block');
            this.warning.prepend(boldMsg);
            this.warning.classList.add('alert-warning', 'p-3', 'm-1', 'd-none', 'ups-warning');

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
     * Checks all payment options and hides them if it is an COD payment option and the delivery is not ups.
     * @param {Event} ev the triggered document event
     * @private
     * @override
     */
    _onCarrierClick: function (ev) {
        this._super(...arguments);

        if (this.codOptions.length === 0) { // Falsy evaluation does not work with NodeList
            return;
        }

        this.warning.classList.add('d-none');

        const input = ev.currentTarget.querySelector('input');
        let atLeastOneOptionAvailable = false;
        for (let option of this.paymentOptions) {
            if (option.dataset.providerCode === "custom" &&
                option.dataset.providerCustomMode === "cash_on_delivery" &&
                (input.dataset.deliveryType !== 'ups' || !input.dataset.upsCod)) {
                    if (option.checked) { // The payment option was selected.
                        this._disablePayButton(); // Reset the submit button.
                    }
                    this._setEnablePaymentOption(option, false);
            } else {
                if (option.dataset.providerCode === "custom" &&
                    option.dataset.providerCustomMode === "cash_on_delivery") {
                    this._setEnablePaymentOption(option, true);
                }
                atLeastOneOptionAvailable = true;
            }
        }

        if (!atLeastOneOptionAvailable) {
            this.warning.classList.remove('d-none');
            this._disablePayButton();
        }
        else {
            this._enableButton();
        }
    }

});
