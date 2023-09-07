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
            if (provider !== 'razorpay_auto') {
                return this._super(...arguments);
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
