/* global TossPayments */

import { loadJS } from '@web/core/assets';
import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    // === DOM MANIPULATION ===

    /**
     * Prepare the inline form of Toss Payments for direct payment.
     *
     * @override method from payment.payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'tosspayments') {
            await super._prepareInlineForm(...arguments);
            return;
        }

        this._setPaymentFlow('direct');

        await this.waitFor(loadJS('https://js.tosspayments.com/v2/standard'));
    },

    // #=== PAYMENT FLOW ===#

    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'tosspayments') {
            await super._processDirectFlow(...arguments);
            return;
        }

        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const clientKey = radio.dataset['tosspaymentsClientKey'];
        const customerKey = processingValues.customer_key;

        const tossPayments = TossPayments(clientKey);
        const payment = tossPayments.payment({ customerKey });

        let paymentMethod
        const paymentMethodMapping = {
            "card": "CARD",
            "virtual_account": "VIRTUAL_ACCOUNT",
            "bank_transfer": "TRANSFER",
            "mobile_phone": "MOBILE_PHONE",
        }
        if (paymentMethodCode in paymentMethodMapping) {
            paymentMethod = paymentMethodMapping[paymentMethodCode]
        }
        else if (paymentMethodCode == "gift_certificate") {
            paymentMethod = document.querySelector(
                'input[name="gift_certificate_type"]:checked'
            ).value
        }
        else {
            this._enableButton();
            this._displayErrorDialog(_t("Unknown payment method"));
        }

        const paymentDetails = {
            method: paymentMethod,
            amount: {
                currency: "KRW",
                value: processingValues.amount,
            },
            orderId: btoa(processingValues.reference),
            orderName: processingValues.products_description,
            successUrl: window.location.origin + "/payment/tosspayments/success",
            failUrl: window.location.origin + "/payment/tosspayments/fail",
            customerName: processingValues.partner_name || "",
            customerEmail: processingValues.partner_email || "",
        }
        // Toss Payments SDK does not accept invalid phone number and will throw error.
        // Note: customer name, email, and phone number are optional values that fills the optional
        // data in the payment widget. It is safer to pass nothing if in doubt.
        if (this.isValidKoreanPhoneNumber(processingValues.partner_phone)) {
            paymentDetails.customerMobilePhone = processingValues.partner_phone;
        }

        payment.requestPayment(paymentDetails)
            .catch(error => {
                this._enableButton();
                if (error.code == "USER_CANCEL") {
                    this._displayErrorDialog(_t("Payment cancelled"), error.message);
                }
                else {
                    this._displayErrorDialog(_t("Payment request error"), error.message);
                }
            })
    },

    // #=== HELPERS ===#

    /**
     * Checks if the `phoneNumber` is a valid Korean phone number.
     * @param {string} phoneNumber
     * @returns {boolean}
     */
    isValidKoreanPhoneNumber(phoneNumber) {
        if (!phoneNumber) return false;
        if (/[^0-9-+]/.test(phoneNumber)) return false;
        if (phoneNumber.indexOf('+', 1) !== -1) return false;

        let cleaned = phoneNumber.replace(/-/g, '');
        if (cleaned.startsWith('+82')) {
            cleaned = '0' + cleaned.substring(3);
        }

        // - Mobile: 010, 011, 016, 017, 018, 019 followed by 7 or 8 digits. (Total 10 or 11 digits)
        // - Landline: Seoul (02) followed by 7 or 8 digits. (Total 9 or 10 digits)
        // - Other regions (031, 032, etc.) followed by 7 or 8 digits. (Total 10 or 11 digits)
        const phoneRegex = /^(01[016789]{1}|02|0[3-9]{1}[0-9]{1})[0-9]{3,4}[0-9]{4}$/;
        return phoneRegex.test(cleaned);
    },
})
