/** @odoo-module **/
/* global Stripe */

import { _t } from '@web/core/l10n/translation';
import { paymentExpressCheckoutForm } from '@payment/js/express_checkout_form';
import { StripeOptions } from '@payment_stripe/js/stripe_options';

paymentExpressCheckoutForm.include({
    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    /**
     * Get the order details to display on the payment form.
     *
     * @private
     * @param {number} deliveryAmount - The delivery costs.
     * @returns {Object} The information to be displayed on the payment form.
     */
    _getOrderDetails(deliveryAmount) {
        const pending = this.paymentContext['shippingInfoRequired'] && deliveryAmount === undefined;
        const minorAmount = parseInt(this.paymentContext['minorAmount'])
        const displayItems = [
            {
                label: _t("Your order"),
                amount: minorAmount,
            },
        ];
        if (this.paymentContext['shippingInfoRequired'] && deliveryAmount !== undefined) {
            displayItems.push({
                label: _t("Delivery"),
                amount: deliveryAmount,
            });
        }
        return {
            total: {
                label: this.paymentContext['merchantName'],
                amount: minorAmount + (deliveryAmount ?? 0),
                // Delay the display of the amount until the shipping price is retrieved.
                pending: pending,
            },
            displayItems: displayItems,
        };
    },

    /**
     * Prepare the express checkout form of Stripe for direct payment.
     *
     * @override method from payment.express_form
     * @private
     * @param {Object} providerData - The provider-specific data.
     * @return {void}
     */
    async _prepareExpressCheckoutForm(providerData) {
        /*
         * When applying a coupon, the amount can be totally covered, with nothing left to pay. In
         * that case, the check is whether the variable is defined because the server doesn't send
         * the value when it equals '0'.
         */
        if (providerData.providerCode !== 'stripe' || !this.paymentContext['amount']) {
            this._super(...arguments);
            return;
        }

        const stripeJS = Stripe(
            providerData.stripePublishableKey,
            new StripeOptions()._prepareStripeOptions(providerData),
        );
        const paymentRequest = stripeJS.paymentRequest({
            country: providerData.countryCode,
            currency: this.paymentContext['currencyName'],
            requestPayerName: true, // Force fetching the billing address for Apple Pay.
            requestPayerEmail: true,
            requestPayerPhone: true,
            requestShipping: this.paymentContext['shippingInfoRequired'],
            ...this._getOrderDetails(),
        });
        if (this.stripePaymentRequests === undefined) {
            this.stripePaymentRequests = [];
        }
        this.stripePaymentRequests.push(paymentRequest);
        const paymentRequestButton = stripeJS.elements().create('paymentRequestButton', {
            paymentRequest: paymentRequest,
            style: {paymentRequestButton: {type: 'buy'}},
        });

        // Check the availability of the Payment Request API first.
        const canMakePayment = await paymentRequest.canMakePayment();
        if (canMakePayment) {
            paymentRequestButton.mount(
                `#o_stripe_express_checkout_container_${providerData.providerId}`
            );
        } else {
            document.querySelector(
                `#o_stripe_express_checkout_container_${providerData.providerId}`
            ).style.display = 'none';
        }

        paymentRequest.on('paymentmethod', async (ev) => {
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
            if (this.paymentContext['shippingInfoRequired']) {
                addresses.shipping_address = {
                    name: ev.shippingAddress.recipient,
                    email: ev.payerEmail,
                    phone: ev.shippingAddress.phone,
                    street: ev.shippingAddress.addressLine[0],
                    street2: ev.shippingAddress.addressLine[1],
                    zip: ev.shippingAddress.postalCode,
                    city: ev.shippingAddress.city,
                    country: ev.shippingAddress.country,
                    state: ev.shippingAddress.region,
                };
                addresses.shipping_option = ev.shippingOption;
            }
            // Update the customer addresses on the related document.
            this.paymentContext.partnerId = parseInt(await this.rpc(
                this.paymentContext['expressCheckoutRoute'],
                addresses,
            ));
            // Call the transaction route to create the transaction and retrieve the client secret.
            const { client_secret } = await this.rpc(
                this.paymentContext['transactionRoute'],
                this._prepareTransactionRouteParams(providerData.providerId),
            );
            // Confirm the PaymentIntent without handling eventual next actions (e.g. 3DS).
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
                if (paymentIntent.status === 'requires_action') { // A next step is required.
                    await stripeJS.confirmCardPayment(client_secret); // Trigger the step.
                }
                window.location = '/payment/status';
            }
        });

        if (this.paymentContext['shippingInfoRequired']) {
            // Wait until the express checkout form is loaded for Apple Pay and Google Pay to select
            // a default shipping address and trigger the `shippingaddresschange` event, so we can
            // fetch the available shipping options. When the customer manually selects a different
            // shipping address, the shipping options need to be fetched again.
            paymentRequest.on('shippingaddresschange', async (ev) => {
                // Call the shipping address update route to fetch the shipping options.
                const availableCarriers = await this.rpc(
                    this.paymentContext['shippingAddressUpdateRoute'],
                    {
                        partial_shipping_address: {
                            zip: ev.shippingAddress.postalCode,
                            city: ev.shippingAddress.city,
                            country: ev.shippingAddress.country,
                            state: ev.shippingAddress.region,
                        },
                    },
                );
                if (availableCarriers.length === 0) {
                    ev.updateWith({status: 'invalid_shipping_address'});
                } else {
                    ev.updateWith({
                        status: 'success',
                        shippingOptions: availableCarriers.map(carrier => ({
                            id: String(carrier.id),
                            label: carrier.name,
                            detail: carrier.description ? carrier.description:'',
                            amount: carrier.minorAmount,
                        })),
                        ...this._getOrderDetails(availableCarriers[0].minorAmount),
                    });
                }
            });

            // When the customer selects a different shipping option, update the displayed total.
            paymentRequest.on('shippingoptionchange', async (ev) => {
                ev.updateWith({
                    status: 'success',
                    ...this._getOrderDetails(ev.shippingOption.amount),
                });
            });
        }
    },

    /**
     * Update the amount of the express checkout form.
     *
     * @override method from payment.express_form
     * @private
     * @param {number} newAmount - The new amount.
     * @param {number} newMinorAmount - The new minor amount.
     * @return {void}
     */
    _updateAmount(newAmount, newMinorAmount) {
        this._super(...arguments);
        this.stripePaymentRequests && this.stripePaymentRequests.map(
            paymentRequest => paymentRequest.update(this._getOrderDetails())
        );
    },
});
