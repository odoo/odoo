/** @odoo-module **/
/* global PaypalCheckout */

import { _t } from '@web/core/l10n/translation';
import paymentForm from '@payment/js/payment_form';
import { rpc, RPCError } from '@web/core/network/rpc';

paymentForm.include({
    inlineFormValues: undefined,
    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of Demo for direct payment.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'paypal') {
            this._super(...arguments);
            return;
        } else if (flow === 'token') {
            return;
        }
        document.getElementById("loading").classList.remove("d-none");
        this._hideInputs();
        this._setPaymentFlow('direct');
        // PayPal Code
        // Helper / Utility functions
        let url_to_head = (url) => {
            return new Promise(function (resolve, reject) {
                var script = document.createElement('script');
                script.src = url;
                script.onload = function () {
                    resolve();
                };
                script.onerror = function () {
                    reject('Error loading script.');
                };
                document.head.appendChild(script);
            });
        }
        const paypal_sdk_url = "https://www.paypal.com/sdk/js";
        //https://developer.paypal.com/sdk/js/configuration/#link-queryparameters
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        this.inlineFormValues = JSON.parse(radio.dataset['paypalInlineFormValues']);
        const paypalColor = radio.dataset['paypalColor']
        const { client_id, currency, intent, amount, payee } = this.inlineFormValues
        url_to_head(
            paypal_sdk_url + "?client-id=" + client_id +
            "&components=buttons" +
            "&currency=" + currency +
            "&intent=" + intent
        ).then(() => {
            document.getElementById("loading").classList.add("d-none");
            let paypal_buttons = paypal.Buttons({ // https://developer.paypal.com/sdk/js/reference
                fundingSource: paypal.FUNDING.PAYPAL,
                onClick: (data) => { // https://developer.paypal.com/sdk/js/reference/#link-oninitonclick
                    //Custom JS here
                },
                style: { //https://developer.paypal.com/sdk/js/reference/#link-style
                    color: paypalColor,
                    label: 'pay'
                },

                createOrder: this._paypalOnSubmit.bind(this),
                onApprove: function (data, actions) {
                    let order_id = data.orderID;
                    console.log("onApprove", data)
                    return rpc("/payment/paypal/complete_order", {
                        "intent": intent,
                        "order_id": order_id
                    })
                        .then(() => {
                            //Close out the PayPal buttons that were rendered
                            paypal_buttons.close();
                            window.location = '/payment/status';
                        })
                        .catch((error) => {
                            console.log("error on approve", error);
                        });
                },

                onCancel: function (data) {
                    this._displayErrorDialog(_t("Payment processing failed"), data);
                },

                onError: function (err) {
                    this._displayErrorDialog(_t("Payment processing failed"), err);
                }
            });
            paypal_buttons.render('#o_provider_payment_submit_button');
        })
            .catch((error) => {
                console.error(error);
            });
    },
    /**
     * Handle the submit event of the component and initiate the payment.
     *
     * @private
     * @param {object} state - The state of the component.
     * @param {object} component - The component.
     * @return {void}
     */
    _paypalOnSubmit(state, component) {
        // Create the transaction and retrieve the processing values.
        const { currency, intent, amount, payee } = this.inlineFormValues
        rpc(
            this.paymentContext['transactionRoute'],
            this._prepareTransactionRouteParams(),
        ).then(processingValues => {
            component.reference = processingValues.reference; // Store final reference.
            // Initiate the payment.
            return rpc('/payment/paypal/create_order', {
                intent: intent,
                currency: currency,
                amount: amount,
                payee: payee,
            }).then((order_id) => {
                console.log("Created order id", order_id)
                return order_id;
            }).catch(error => {
                if (error instanceof RPCError) {
                    inlineForm._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                } else {
                    return Promise.reject(error);
                }
            });
        })
    },
    // #=== PAYMENT FLOW ===#

    /**
     * Simulate a feedback from a payment provider and redirect the customer to the status page.
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
        if (providerCode !== 'paypal') {
            this._super(...arguments);
            return;
        }
    },

});
