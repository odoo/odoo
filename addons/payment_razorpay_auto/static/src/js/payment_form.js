/** @odoo-module **/
/* global Razorpay */

import { _t } from "@web/core/l10n/translation";
import checkoutForm from "@payment/js/checkout_form";
import manageForm from "@payment/js/manage_form";


const razorpayMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add `sale_order_id` to the transaction route params if it is provided.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} code - The code of the selected payment option's provider
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {object} The extended transaction route params
     */
    _prepareTransactionRouteParams: function (code, paymentOptionId, flow) {
        const transactionRouteParams = this._super(...arguments);
        if (code !== 'razorpay') {
            return transactionRouteParams;
        }
        let paymentMethod = false;
        const paymentMethodCardInput = document.getElementById('pament_method_card');
        const paymentMethodUpiInput = document.getElementById('pament_method_upi');
        if (paymentMethodCardInput.checked) {
            paymentMethod = paymentMethodCardInput.value;
        }
        else if (paymentMethodUpiInput.checked) {
            paymentMethod = paymentMethodUpiInput.value;
        }
        return {
            ...transactionRouteParams,
            'razorpay_payment_method': paymentMethod,
        };
    },

     /**
     * Redirect the customer to Razorpay hosted payment page.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider - The provider of the payment option's acquirer
     * @param {number} paymentOptionId - The id of the payment option handling the transaction
     * @param {object} processingValues - The processing values of the transaction
     * @return {undefined}
     */
    _processRedirectPayment(provider, paymentOptionId, processingValues) {
        if (provider !== 'razorpay' || !(this.txContext.tokenizationRequested || processingValues.is_tokenize_request)) {
            this._super(...arguments);
            return;
        }
        const razorpayOptions = this._prepareRazorpayOptions(processingValues);
        const rzp = Razorpay(razorpayOptions);
        rzp.open();
        rzp.on('payment.failed', (resp) => {
            this._displayError(
                _t("Server Error"),
                _t("We are not able to process your payment."),
                resp.error.description,
            );
        });
    },

    /**
     * Prepare the options to init the RazorPay JS Object
     *
     * Function overriden in internal module
     *
     * @param {object} processingValues
     * @return {object}
     */
    _prepareRazorpayOptions(processingValues) {
        return Object.assign({}, processingValues, {
            "key": processingValues.razorpay_key_id,
            "order_id": processingValues.order_id,
            "customer_id": processingValues.customer_id,
            "description": processingValues.reference,
            "recurring": "1",
            "handler": (resp) => {
                if (resp.razorpay_payment_id && resp.razorpay_order_id && resp.razorpay_signature) {
                    window.location = '/payment/status';

                }
            },
            "modal": {
                "ondismiss": () => {
                        window.location.reload();
                    }
            },
        });
    },

};

checkoutForm.include(razorpayMixin);
manageForm.include(razorpayMixin);
