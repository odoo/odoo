/* global Stripe */

import { ExpressCheckout } from '@payment/interactions/express_checkout';
import { StripeOptions } from '@payment_stripe/interactions/stripe_options';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';
import { redirect } from '@web/core/utils/urls';

patch(ExpressCheckout.prototype, {
    /**
     * Get the order details to display on the payment form.
     *
     * @private
     * @param {number} deliveryAmount - The delivery costs.
     * @param {number} amountFreeShipping - The free shipping discount amount, <= 0.
     * @param {number} orderMinorAmount - The order amount without delivery, in minor units.
     * @returns {Object} The information to be displayed on the payment form.
     */
    _getOrderDetails(
        deliveryAmount, amountFreeShipping, orderMinorAmount = this.paymentContext['minorAmount']
    ) {
        const minorAmount = parseInt(orderMinorAmount || 0);
        const displayItems = [{
            name: _t("Your order"),
            amount: minorAmount,
        }];
        if (this.paymentContext['shippingInfoRequired'] && deliveryAmount !== undefined) {
            displayItems.push({
                name: _t("Delivery"),
                amount: deliveryAmount,
            });
        }
        if (amountFreeShipping) {
            displayItems.push({
                name: _t("Free Shipping"),
                amount: amountFreeShipping,
            });
        }
        return {
            amount: minorAmount + (deliveryAmount ?? 0) + (amountFreeShipping ?? 0),
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
            super._prepareExpressCheckoutForm(...arguments);
            return;
        }

        const stripeJS = Stripe(
            providerData.stripePublishableKey,
            new StripeOptions()._prepareStripeOptions(providerData),
        );
        const elements = stripeJS.elements({
            mode: 'payment',
            currency: this.paymentContext['currencyName'],
            amount: this._getOrderDetails().amount,
            captureMethod: providerData.captureMethod,
            allowedPaymentMethodTypes: ['card'], // Apple Pay and Google Pay
        });
        (this.stripeElements ??= []).push(elements);

        const expressCheckoutElement = elements.create('expressCheckout', {
            business: {name: this.paymentContext['merchantName']},
            billingAddressRequired: true, // Force fetching the billing address for Apple Pay
            emailRequired: true,
            phoneNumberRequired: true,
            shippingAddressRequired: Boolean(this.paymentContext['shippingInfoRequired']),
            buttonType: {applePay: 'buy', googlePay: 'buy'},
        });
        const container = document.querySelector(
            `#o_stripe_express_checkout_container_${providerData.providerId}`
        );
        // Show the express checkout form only if a payment method is available
        expressCheckoutElement.on('availablepaymentmethodschange', ({ paymentMethods }) => {
            container.hidden = !paymentMethods;
        });
        expressCheckoutElement.mount(container);
        this.registerCleanup(() => expressCheckoutElement.destroy());

        // The order amount adjusted to the shipping address, only valid while the sheet is open
        let sheetMinorAmount;
        // Display the line items when the payment interface opens
        expressCheckoutElement.on('click', (ev) => {
            sheetMinorAmount = this.paymentContext['minorAmount'];
            ev.resolve({lineItems: this._getOrderDetails().displayItems});
        });

        // Restore the amount if the customer closes the payment interface after selecting a
        // shipping address or rate
        expressCheckoutElement.on('cancel', () => {
            elements.update({amount: this._getOrderDetails().amount});
        });

        expressCheckoutElement.on('confirm', async (ev) => {
            // Validate the payment details before any asynchronous work
            const { error: submitError } = await this.waitFor(elements.submit());
            if (submitError) {
                ev.paymentFailed();
                return;
            }
            const { name, email, phone, address } = ev.billingDetails;
            const addresses = {
                'billing_address': {name, email, phone, ...this._toOdooAddress(address)},
            };
            if (this.paymentContext['shippingInfoRequired']) {
                addresses.shipping_address = {
                    name: ev.shippingAddress.name,
                    email,
                    phone,
                    ...this._toOdooAddress(ev.shippingAddress.address),
                };
                addresses.shipping_option = ev.shippingRate;
            }
            // Update the customer addresses on the related document.
            try {
                this.paymentContext.partnerId = parseInt(await this.waitFor(rpc(
                    this.paymentContext['expressCheckoutRoute'],
                    addresses,
                )));
            } catch {
                ev.paymentFailed();
                return;
            }
            // Call the transaction route to create the transaction and retrieve the client secret.
            const { client_secret, return_url } = await this._prepareExpressTransaction();
            if (!client_secret) {
                ev.paymentFailed();
                return;
            }
            // Confirm the PaymentIntent and handle eventual next actions (e.g. 3DS)
            const { error: confirmError } = await this.waitFor(stripeJS.confirmPayment({
                elements,
                clientSecret: client_secret,
                confirmParams: {return_url},
                redirect: 'if_required',
            }));
            if (confirmError) {
                this._displayErrorDialog(_t("Payment processing failed"), confirmError.message);
            } else {
                redirect('/payment/status');
            }
        });

        if (this.paymentContext['shippingInfoRequired']) {
            // Wait until the express checkout form is loaded for Apple Pay and Google Pay to select
            // a default shipping address and trigger the `shippingaddresschange` event, so we can
            // fetch the available shipping options. When the customer manually selects a different
            // shipping address, the shipping options need to be fetched again.
            expressCheckoutElement.on('shippingaddresschange', async (ev) => {
                // Call the shipping address update route to fetch the shipping options.
                let availableCarriersData;
                try {
                    availableCarriersData = await this.waitFor(rpc(
                        this.paymentContext['shippingAddressUpdateRoute'],
                        {partial_delivery_address: this._toOdooAddress(ev.address)},
                    ));
                } catch {
                    ev.reject();
                    return;
                }
                const {
                    delivery_methods, delivery_discount_minor_amount, adjusted_minor_amount
                } = availableCarriersData;
                if (availableCarriersData.external_tax_error || delivery_methods.length === 0) {
                    ev.reject();
                } else {
                    sheetMinorAmount = adjusted_minor_amount;
                    const orderDetails = this._getOrderDetails(
                        delivery_methods[0].minorAmount,
                        delivery_discount_minor_amount,
                        sheetMinorAmount,
                    );
                    await this.waitFor(elements.update({amount: orderDetails.amount}));
                    ev.resolve({
                        shippingRates: delivery_methods.map(carrier => ({
                            id: String(carrier.id),
                            displayName: carrier.name,
                            amount: carrier.minorAmount,
                        })),
                        lineItems: orderDetails.displayItems,
                    });
                }
            });

            // When the customer selects a different shipping option, update the displayed total.
            expressCheckoutElement.on('shippingratechange', async (ev) => {
                let result;
                try {
                    result = await this.waitFor(rpc('/shop/set_delivery_method', {
                        dm_id: parseInt(ev.shippingRate.id),
                    }));
                } catch {
                    ev.reject();
                    return;
                }
                const orderDetails = this._getOrderDetails(
                    ev.shippingRate.amount,
                    parseInt(result.delivery_discount_minor_amount) || 0,
                    sheetMinorAmount,
                );
                await this.waitFor(elements.update({amount: orderDetails.amount}));
                ev.resolve({lineItems: orderDetails.displayItems});
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
        super._updateAmount(...arguments);
        // Elements requires a positive amount; the form is hidden by `super` when nothing is due
        if (this.paymentContext.amount) {
            const amount = this._getOrderDetails().amount;
            this.stripeElements?.forEach(elements => elements.update({amount}));
        }
    },

    /**
     * Convert a Stripe address into the address fields expected by the express checkout routes.
     *
     * @private
     * @param {Object} address - The Stripe address.
     * @return {Object} The Odoo address fields.
     */
    _toOdooAddress(address) {
        return {
            street: address.line1,
            street2: address.line2,
            zip: address.postal_code,
            city: address.city,
            country: address.country,
            state: address.state,
        };
    },
});
