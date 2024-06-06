/** @odoo-module **/
/* global PaypalCheckout */

import paymentForm from '@payment/js/payment_form';
import { rpc, RPCError } from '@web/core/network/rpc';

paymentForm.include({
    paypalCheckout: undefined,
    paypalComponents: undefined,

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
        const inlineFormValues = JSON.parse(radio.dataset['paypalInlineFormValues']);
        const paypalColor = radio.dataset['paypalColor']
        const { client_id, currency, intent, amount } = inlineFormValues
        console.log('inlineFormValues', inlineFormValues)
        url_to_head(
            paypal_sdk_url + "?client-id=" + client_id +
            "&components=buttons" +
            "&currency=" + currency +
            "&intent=" + intent.toLowerCase()
        )
            .then(() => {
                document.getElementById("loading").classList.add("d-none");
                let paypal_buttons = paypal.Buttons({ // https://developer.paypal.com/sdk/js/reference
                    fundingSource: paypal.FUNDING.PAYPAL,
                    onClick: (data) => { // https://developer.paypal.com/sdk/js/reference/#link-oninitonclick
                        //Custom JS here
                    },
                    style: { //https://developer.paypal.com/sdk/js/reference/#link-style
                        color: paypalColor,
                        label:'pay'
                    },

                    createOrder: function (data, actions) { //https://developer.paypal.com/docs/api/orders/v2/#orders_create
                        return rpc('/payment/paypal/create_order', {
                            intent: intent,
                            currency: currency,
                            amount: amount,
                        })
                            .then((order_id) => {
                                console.log("Created order id", order_id)
                                return order_id;
                            }).catch(error => {
                                if (error instanceof RPCError) {
                                    this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                                } else {
                                    return Promise.reject(error);
                                }
                            });
                    },

                    onApprove: function (data, actions) {
                        let order_id = data.orderID;
                        console.log("onApprove", data)
                        return rpc("/payment/paypal/complete_order", {
                            "intent": intent,
                            "order_id": order_id
                        })
                            .then((response) => response.json())
                            .then((order_details) => {
                                console.log(order_details); //https://developer.paypal.com/docs/api/orders/v2/#orders_capture!c=201&path=create_time&t=response
                                let intent_object = intent === "authorize" ? "authorizations" : "captures";
                                //Custom Successful Message
                                console.log(
                                    order_details.payer.name.given_name + ` ` +
                                    order_details.payer.name.surname + ` for your payment of ` +
                                    order_details.purchase_units[0].payments[intent_object][0].amount.value + ` ` +
                                    order_details.purchase_units[0].payments[intent_object][0].amount.currency_code
                                );

                                //Close out the PayPal buttons that were rendered
                                paypal_buttons.close();
                            })
                            .catch((error) => {
                                console.log("error on approve", error);
                            });
                    },

                    onCancel: function (data) {
                        console.log("onCancel", data);
                    },

                    onError: function (err) {
                        console.log("onError", err);
                    }
                });
                paypal_buttons.render('#o_provider_payment_submit_button');
            })
            .catch((error) => {
                console.error(error);
            });
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
