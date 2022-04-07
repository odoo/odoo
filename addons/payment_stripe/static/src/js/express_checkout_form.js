/** @odoo-module **/
/* global Stripe */

import { _t } from "@web/core/l10n/translation";
import { paymentExpressCheckoutForm } from '@payment/js/express_checkout_form';
import { _prepareStripeOptions } from 'payment_stripe.payment_form';

paymentExpressCheckoutForm.include({

    /**
     * Prepare the express checkout form of Stripe for direct payment.
     *
     * @override method from payment.express_form
     * @private
     * @param {Object} acquirerData - The acquirer-specific data.
     * @return {Promise}
     */
    async _prepareExpressCheckoutForm(acquirerData) {
        if (acquirerData.provider !== 'stripe') {
            return this._super(...arguments);
        }

        const isShippingInformationRequired = this._isShippingInformationRequired();
        const stripeJS = Stripe(
            acquirerData.stripePublishableKey, _prepareStripeOptions(acquirerData)
        );
        this.stripeExpressCheckoutForm = stripeJS.paymentRequest({
            country: acquirerData.countryCode,
            currency: this.txContext.currencyName,
            total: {
                label: this.txContext.merchantName,
                amount: this.txContext.minorAmount,
                // Delay the display of the amount until the shipping price is retrieved.
                pending: isShippingInformationRequired,
            },
            displayItems: !isShippingInformationRequired ? [] : [
                {
                    label: _t("Your order"),
                    amount: this.txContext.minorAmount,
                },
                {
                    label: _t("Delivery"),
                    amount: 0,
                },
            ],
            requestPayerName: true, // Force fetching the billing address for Apple Pay.
            requestPayerEmail: true,
            requestPayerPhone: true,
            requestShipping: isShippingInformationRequired,
        });
        const paymentRequestButton = stripeJS.elements().create('paymentRequestButton', {
            paymentRequest: this.stripeExpressCheckoutForm,
            style: {paymentRequestButton: {type: 'buy'}},
        });
        await (async () => {
            // Check the availability of the Payment Request API first.
            const canMakePayment = await this.stripeExpressCheckoutForm.canMakePayment();
            if (canMakePayment) {
                paymentRequestButton.mount(
                    `#o_stripe_express_checkout_container_${acquirerData.acquirerId}`
                );
            } else {
                document.querySelector(
                    `#o_stripe_express_checkout_container_${acquirerData.acquirerId}`
                ).style.display = 'none';
            }
        })();

        this.stripeExpressCheckoutForm.on('paymentmethod', async (ev) => {
            const addresses = {
                'billing_address': {
                    name: ev.payerName,
                    email: ev.payerEmail,
                    phone: ev.payerPhone,
                    street: ev.paymentMethod.billing_details.address.line1,
                    street2: ev.paymentMethod.billing_details.address.line2,
                    zip: ev.paymentMethod.billing_details.address.postal_code,
                    city: ev.paymentMethod.billing_details.address.city,
                    country: ev.paymentMethod.billing_details.address.country,
                    state: ev.paymentMethod.billing_details.address.state,
                }
            };
            if (isShippingInformationRequired) {
                Object.assign(addresses, {
                    'shipping_address': {
                        name: ev.shippingAddress.recipient,
                        phone: ev.shippingAddress.phone,
                        street: ev.shippingAddress.addressLine[0],
                        street2: ev.shippingAddress.addressLine[1],
                        zip: ev.shippingAddress.postalCode,
                        city: ev.shippingAddress.city,
                        country: ev.shippingAddress.country,
                        state: ev.shippingAddress.region,
                    },
                    'shipping_option': ev.shippingOption,
                });
            }
            // Update the customer addresses on the related document.
            this.txContext.partnerId = parseInt(await this._rpc({
                route: this.txContext.expressRoute, params: addresses,
            }));
            // Call the transaction route to create the transaction and retrieve the client secret.
            const { client_secret } = await this._rpc({
                route: this.txContext.transactionRoute,
                params: this._prepareTransactionRouteParams(acquirerData.acquirerId),
            });
            // Confirm the PaymentIntent without handling eventual next actions.
            const { paymentIntent, error: confirmError } = await stripeJS.confirmCardPayment(
                client_secret, {payment_method: ev.paymentMethod.id}, {handleActions: false}
            );
            if (confirmError) {
                // Report to the browser that the payment failed, prompting it to re-show the
                // payment interface, or show an error message and close the payment interface.
                ev.complete('fail');
            } else {
                // Report to the browser that the confirmation was successful, prompting it to close
                // the browser payment method collection interface.
                ev.complete('success');
                // Check if the PaymentIntent requires any actions and, if so, let Stripe.js handle
                // the flow.
                if (paymentIntent.status !== 'requires_action') { // The payment has succeeded.
                    window.location = '/payment/status';
                } else { // A next step is required from the customer, trigger it.
                    const { error } = await stripeJS.confirmCardPayment(client_secret);
                    if (!error) { // The payment has succeeded.
                        window.location = '/payment/status';
                    }
                }
            }
        });

        if (isShippingInformationRequired) {
            // Wait until the express checkout form is loaded for Apple Pay and Google Pay to select
            // a default shipping address and trigger the `shippingaddresschange` event, so we can
            // fetch the available shipping options. When the customer manually selects a different
            // shipping address, the shipping options need to be fetched again.
            this.stripeExpressCheckoutForm.on('shippingaddresschange', async (ev) => {
                // Call the shipping address update route to fetch the shipping options.
                const availableCarriers = await this._rpc({
                    route: this.txContext.shippingAddressUpdateRoute,
                    params: {
                        partial_shipping_address: {
                            zip: ev.shippingAddress.postalCode,
                            city: ev.shippingAddress.city,
                            country: ev.shippingAddress.country,
                            state: ev.shippingAddress.region,
                        },
                    },
                });
                if (availableCarriers.length === 0) {
                    ev.updateWith({status: 'invalid_shipping_address'});
                } else {
                    ev.updateWith({
                        status: 'success',
                        shippingOptions: availableCarriers.map(carrier => ({
                            id: String(carrier.id),
                            label: carrier.name,
                            detail: carrier.description ? carrier.description:"",
                            amount: carrier.minorAmount,
                        })),
                        total: {
                            label: this.txContext.merchantName,
                            amount: this.txContext.minorAmount + availableCarriers[0].minorAmount,
                            pending: false,
                        },
                        displayItems: [
                            {
                                label: _t("Your order"),
                                amount: this.txContext.minorAmount,
                            },
                            {
                                label: _t("Delivery"),
                                amount: availableCarriers[0].minorAmount,
                            },
                        ],
                    });
                }
            });

            // When the customer selects a different shipping option, update the displayed total.
            this.stripeExpressCheckoutForm.on('shippingoptionchange', async (ev) => {
                ev.updateWith({
                    status: 'success',
                    total: {
                        label: this.txContext.merchantName,
                        amount: this.txContext.minorAmount + ev.shippingOption.amount,
                        pending: false,
                    },
                    displayItems: [
                        {
                            label: _t("Your order"),
                            amount: this.txContext.minorAmount,
                        },
                        {
                            label: _t("Delivery"),
                            amount: ev.shippingOption.amount, // Already in minor amount.
                        },
                    ],
                });
            });
        }
    },

    /**
     * Update the amount of the express checkout form.
     *
     * @override method from payment.express_form
     * @private
     * @param {Object} acquirerData - The acquirer-specific data.
     * @param {number} newAmount - The new amount.
     * @param {number} newMinorAmount - The new minor amount.
     * @return {undefined}
     */
    _updateAmount(acquirerData, newAmount, newMinorAmount) {
        if (acquirerData.provider !== 'stripe') {
            return this._super(...arguments);
        }

        this.txContext.amount = parseFloat(newAmount);
        this.txContext.minorAmount = parseInt(newMinorAmount);
        this.stripeExpressCheckoutForm.update({
            total: {
                amount: parseInt(newMinorAmount),
                label: this.txContext.merchantName,
            }
        });
    },
});
