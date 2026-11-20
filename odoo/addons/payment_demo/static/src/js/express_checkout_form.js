/** @odoo-module */

import {_t} from '@web/core/l10n/translation';
import publicWidget from '@web/legacy/js/public/public_widget';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { jsonrpc } from '@web/core/network/rpc_service';
import { debounce } from '@web/core/utils/timing';

import { paymentExpressCheckoutForm } from '@payment/js/express_checkout_form';
import paymentDemoMixin from '@payment_demo/js/payment_demo_mixin';

paymentExpressCheckoutForm.include({
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click button[name="o_payment_submit_button"]': '_initiateExpressPayment',
    }),

    // #=== WIDGET LIFECYCLE ===#

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        document.querySelector('[name="o_payment_submit_button"]')?.removeAttribute('disabled');
        this.rpc = this.bindService('rpc');
        this._initiateExpressPayment = debounce(this._initiateExpressPayment, 500, true);
    },

    // #=== EVENT HANDLERS ===#

    /**
     * Process the payment.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _initiateExpressPayment(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const shippingInformationRequired = document.querySelector(
            '[name="o_payment_express_checkout_form"]'
        ).dataset.shippingInfoRequired;
        const providerId = ev.target.parentElement.dataset.providerId;
        let expressShippingAddress = {};
        if (shippingInformationRequired){
            const shippingInfo = document.querySelector(
                `#o_payment_demo_shipping_info_${providerId}`
            );
            expressShippingAddress =  {
                'name': shippingInfo.querySelector('#o_payment_demo_shipping_name').value,
                'email': shippingInfo.querySelector('#o_payment_demo_shipping_email').value,
                'street': shippingInfo.querySelector('#o_payment_demo_shipping_address').value,
                'street2': shippingInfo.querySelector('#o_payment_demo_shipping_address2').value,
                'zip': shippingInfo.querySelector('#o_payment_demo_shipping_zip').value,
                'city': shippingInfo.querySelector('#o_payment_demo_shipping_city').value,
                'country': shippingInfo.querySelector('#o_payment_demo_shipping_country').value,
            };
            // Call the shipping address update route to fetch the shipping options.
            const availableCarriers = await this.rpc(
                this.paymentContext['shippingAddressUpdateRoute'],
                {partial_shipping_address: expressShippingAddress},
            );
            if (availableCarriers.length > 0) {
                const id = parseInt(availableCarriers[0].id);
                await this.rpc('/shop/update_carrier', {carrier_id: id});
            } else {
                this.call('dialog', 'add', ConfirmationDialog, {
                    title: _t("Validation Error"),
                    body: _t("No delivery method is available."),
                });
                return;
            }
        }
        await jsonrpc(
            document.querySelector(
                '[name="o_payment_express_checkout_form"]'
            ).dataset['expressCheckoutRoute'],
            {
                'shipping_address': expressShippingAddress,
                'billing_address': {
                    'name': 'Demo User',
                    'email': 'demo@test.com',
                    'street': 'Rue des Bourlottes 9',
                    'street2': '23',
                    'country': 'BE',
                    'city':'Ramillies',
                    'zip':'1367'
                },
            }
        );
        const processingValues = await jsonrpc(
            this.paymentContext['transactionRoute'],
            this._prepareTransactionRouteParams(providerId),
        )
        paymentDemoMixin.processDemoPayment(processingValues);
    },
});
