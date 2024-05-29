/** @odoo-module **/
/* global PaypalCheckout */

import paymentForm from '@payment/js/payment_form';
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
let handle_close = (event) => {
    event.target.closest(".ms-alert").remove();
}
let handle_click = (event) => {
    if (event.target.classList.contains("ms-close")) {
        handle_close(event);
    }
}
document.addEventListener("click", handle_click);
const paypal_sdk_url = "https://www.paypal.com/sdk/js";
const client_id = "AWfClPjf6ZGUf9vpa06Un6RT4e0v4PA4m_6VzXHaGY_rZqeL8QtI5vcvZCrcyicnI7nMXiq0jVfofSGJ";
const currency = "USD";
const intent = "capture";
console.log("HERE")
paymentForm.include({
    adyenCheckout: undefined,
    adyenComponents: undefined,

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
        this._setPaymentFlow('direct');
        //PayPal Code
        //https://developer.paypal.com/sdk/js/configuration/#link-queryparameters
        url_to_head(paypal_sdk_url + "?client-id=" + client_id + "&enable-funding=venmo&currency=" + currency + "&intent=" + intent)
            .then(() => {
                //Handle loading spinner
                // document.getElementById("loading").classList.add("hide");
                // document.getElementById("content").classList.remove("hide");
                let alerts = document.getElementById("alerts");
                let paypal_buttons = paypal.Buttons({ // https://developer.paypal.com/sdk/js/reference
                    onClick: (data) => { // https://developer.paypal.com/sdk/js/reference/#link-oninitonclick
                        //Custom JS here
                    },
                    style: { //https://developer.paypal.com/sdk/js/reference/#link-style
                        shape: 'rect',
                        color: 'gold',
                        layout: 'vertical',
                        label: 'paypal'
                    },

                    createOrder: function (data, actions) { //https://developer.paypal.com/docs/api/orders/v2/#orders_create
                        rpc('/payment/paypal/create_order', {"intent": intent})
                        .then((response) => response.json())
                            .then((order) => { return order.id; }).catch(error => {
                            if (error instanceof RPCError) {
                                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                            } else {
                                return Promise.reject(error);
                            }
                        });
                    },

                    onApprove: function (data, actions) {
                        let order_id = data.orderID;
                        return fetch("http://localhost:3000/complete_order", {
                            method: "post", headers: { "Content-Type": "application/json; charset=utf-8" },
                            body: JSON.stringify({
                                "intent": intent,
                                "order_id": order_id
                            })
                        })
                            .then((response) => response.json())
                            .then((order_details) => {
                                console.log(order_details); //https://developer.paypal.com/docs/api/orders/v2/#orders_capture!c=201&path=create_time&t=response
                                let intent_object = intent === "authorize" ? "authorizations" : "captures";
                                //Custom Successful Message
                                alerts.innerHTML = `<div class=\'ms-alert ms-action\'>Thank you ` + order_details.payer.name.given_name + ` ` + order_details.payer.name.surname + ` for your payment of ` + order_details.purchase_units[0].payments[intent_object][0].amount.value + ` ` + order_details.purchase_units[0].payments[intent_object][0].amount.currency_code + `!</div>`;

                                //Close out the PayPal buttons that were rendered
                                paypal_buttons.close();
                            })
                            .catch((error) => {
                                console.log(error);
                                alerts.innerHTML = `<div class="ms-alert ms-action2 ms-small"><span class="ms-close"></span><p>An Error Ocurred!</p>  </div>`;
                            });
                    },

                    onCancel: function (data) {
                        alerts.innerHTML = `<div class="ms-alert ms-action2 ms-small"><span class="ms-close"></span><p>Order cancelled!</p>  </div>`;
                    },

                    onError: function (err) {
                        console.log(err);
                    }
                });
                const inlineForm = this._getInlineForm(radio);
                const adyenContainer = inlineForm.querySelector('[name="o_adyen_component_container"]');
                this.adyenComponents[paymentOptionId] = this.adyenCheckout.create(
                    inlineFormValues['adyen_pm_code'], componentConfiguration
                ).mount(adyenContainer);
                paypal_buttons.render('#payment_options');
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
