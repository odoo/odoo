/** @odoo-module */

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import "@website_sale/js/website_sale_delivery";

publicWidget.registry.websiteSaleDelivery.include({
    start: function () {
        this.ShiprocketCodOptions = document.querySelectorAll(
            'input[name="o_payment_radio"][data-payment-method-code="shiprocket_cash_on_delivery"]'
        );
        if (this.ShiprocketCodOptions.length > 0) {
            this.paymentOptions = document.querySelectorAll('input[name="o_payment_radio"]');

            this.alertPayment = renderToElement("website_sale_shiprocket.alert_no_payment", {});
            this.paymentMethodsContainer = document.querySelector("#payment_method");
            this.paymentMethodsContainer
                .querySelector("#o_payment_form_options")
                .append(this.alertPayment);
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
            node.classList.remove("d-none");
            node.classList.add("list-group-item");
        } else {
            node.classList.add("d-none");
            node.classList.remove("list-group-item");
            radio.checked = false;
        }
    },

    /**
     * Show only 'Shiprocket: Cash on Delivery' payment method when carrier is Shiprocket with payment method as COD.
     * @param {Event} ev the triggered document event
     * @private
     * @override
     */
    _onCarrierClick: function (ev) {
        this._super(...arguments);
        const input = ev.currentTarget.querySelector("input");
        const submitButton = document.getElementsByName("o_payment_submit_button")[0];
        if (submitButton) {
            if (input.dataset.shiprocketPaymentMethod === "cod" && input.checked) {
                submitButton.textContent = _t("Place Order");
            } else {
                submitButton.textContent = _t("Pay Now");
            }
        }
        if (this.ShiprocketCodOptions.length === 0) {
            return;
        }
        this.alertPayment.classList.add("d-none");

        let atLeastOneOptionAvailable = false;
        for (const option of this.paymentOptions) {
            if (
                option.dataset.providerCode === "custom" &&
                option.dataset.paymentMethodCode === "shiprocket_cash_on_delivery" &&
                input.getAttribute("delivery_type") === "shiprocket" &&
                input.dataset.shiprocketPaymentMethod === "cod"
            ) {
                this._setEnablePaymentOption(option, true);
                atLeastOneOptionAvailable = true;
            } else {
                if (option.checked) {
                    this._disablePayButton(); // Reset the submit button.
                }
                if (
                    option.dataset.paymentMethodCode !== "shiprocket_cash_on_delivery" &&
                    input.dataset.shiprocketPaymentMethod !== "cod"
                ) {
                    this._setEnablePaymentOption(option, true);
                    atLeastOneOptionAvailable = true;
                } else {
                    this._setEnablePaymentOption(option, false);
                }
            }
        }

        if (!atLeastOneOptionAvailable) {
            this.alertPayment.classList.remove("d-none");
            this._disablePayButton();
        } else {
            this._enableButton();
        }
    },
});
