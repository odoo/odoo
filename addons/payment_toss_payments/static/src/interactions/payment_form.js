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
        if (providerCode !== 'toss_payments') {
            await super._prepareInlineForm(...arguments);
            return;
        }

        // Overwrite the flow of the selected payment method.
        this._setPaymentFlow('direct');
    },

    // === PAYMENT FLOW ===

    /**
     * Process Toss Payments' implementation of the direct payment flow.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'toss_payments') {
            await super._processDirectFlow(...arguments);
            return;
        }

        await this.waitFor(loadJS('https://js.tosspayments.com/v2/standard'));

        // Extract and deserialize the inline form values.
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineFormValues = JSON.parse(radio.dataset['tossPaymentsInlineFormValues']);
        const clientKey = inlineFormValues.client_key;
        const paymentMethod = inlineFormValues.toss_payments_pm_code;

        // Open the payment window in modal.
        const paymentDetails = {
            method: paymentMethod,
            amount: {
                currency: 'KRW',
                value: processingValues.amount,
            },
            orderId: processingValues.reference,
            orderName: processingValues.order_name,
            successUrl: processingValues.success_url,
            failUrl: processingValues.fail_url,
            customerName: processingValues.partner_name,
            customerEmail: processingValues.partner_email,
        };
        // Toss Payments SDK does not accept invalid phone numbers and will throw error.
        // Note: customer name, email, and phone number are optional values that fills the optional
        // data in the payment window. It is safer to pass nothing if in doubt.
        const partnerPhoneSanitized = this.sanitizeKoreanPhoneNumber(
            processingValues.partner_phone
        );
        if (partnerPhoneSanitized) {
            paymentDetails.customerMobilePhone = partnerPhoneSanitized;
        }
        const tossPayments = TossPayments(clientKey);
        const payment = tossPayments.payment({ customerKey: TossPayments.ANONYMOUS });
        payment.requestPayment(paymentDetails).catch(error => {
            this._enableButton();
            if (error.code === 'USER_CANCEL') {
                this._displayErrorDialog(_t("Payment not completed"), error.message);
            }
            else {
                this._displayErrorDialog(_t("Payment processing failed"), error.message);
            }
        });
    },

    // === HELPERS ===

    /**
     * Sanitizes the phone number to matches the Toss Payments SDK requirements.
     * @param {string} phoneNumber - The phone number to sanitize.
     * @return {string} The sanitized phone number, or an empty string if the phone number is
     *                  invalid.
     */
    sanitizeKoreanPhoneNumber(phoneNumber) {
        if (!phoneNumber) return "";

        let sanitized = phoneNumber.replace(/[-\s]/g, '');
        if (sanitized.startsWith('+82')) {
            sanitized = '0' + sanitized.substring(3);
        }

        // - Mobile: 010, 011, 016, 017, 018, 019 followed by 7 or 8 digits. (Total 10 or 11 digits)
        // - Landline: Seoul (02) followed by 7 or 8 digits. (Total 9 or 10 digits)
        // - Other regions (031, 032, etc.) followed by 7 or 8 digits. (Total 10 or 11 digits)
        const phoneRegex = /^(01[016789]{1}|02|0[3-9]{1}[0-9]{1})[0-9]{3,4}[0-9]{4}$/;

        if (phoneRegex.test(sanitized)) {
            return sanitized;
        }
        return '';
    },
});
