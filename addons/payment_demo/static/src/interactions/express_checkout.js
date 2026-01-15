
import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { ExpressCheckout } from '@payment/interactions/express_checkout';
import paymentDemoMixin from '@payment_demo/interactions/payment_demo_mixin';

patch(ExpressCheckout.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'button[name="o_payment_submit_button"]': {
                't-on-click.stop.prevent': this.debounced(
                    this.initiateExpressPayment.bind(this), 500, true
                ),
            },
        });
        document.querySelector('[name="o_payment_submit_button"]')?.removeAttribute('disabled');
    },

    /**
     * Process the payment.
     *
     * @param {Event} ev
     * @return {void}
     */
    async initiateExpressPayment(ev) {
        const providerId = ev.target.parentElement.dataset.providerId;
        let expressDeliveryAddress = {};
        if (this.paymentContext.shippingInfoRequired) {
            const shippingInfo = document.querySelector(
                `#o_payment_demo_shipping_info_${providerId}`
            );
            expressDeliveryAddress = {
                'name': shippingInfo.querySelector('#o_payment_demo_shipping_name').value,
                'email': shippingInfo.querySelector('#o_payment_demo_shipping_email').value,
                'street': shippingInfo.querySelector('#o_payment_demo_shipping_address').value,
                'street2': shippingInfo.querySelector('#o_payment_demo_shipping_address2').value,
                'zip': shippingInfo.querySelector('#o_payment_demo_shipping_zip').value,
                'city': shippingInfo.querySelector('#o_payment_demo_shipping_city').value,
                'country': shippingInfo.querySelector('#o_payment_demo_shipping_country').value,
            };
            // Call the shipping address update route to fetch the shipping options.
            const { delivery_methods } = await this.waitFor(rpc(
                this.paymentContext['shippingAddressUpdateRoute'],
                {partial_delivery_address: expressDeliveryAddress},
            ));
            if (delivery_methods.length > 0) {
                const id = parseInt(delivery_methods[0].id);
                await this.waitFor(rpc('/shop/set_delivery_method', {dm_id: id}));
            } else {
                this.services.dialog.add(ConfirmationDialog, {
                    title: _t("Validation Error"),
                    body: _t("No delivery method is available."),
                });
                return;
            }
        }
        await this.waitFor(rpc(
            document.querySelector(
                '[name="o_payment_express_checkout_form"]'
            ).dataset['expressCheckoutRoute'],
            {
                'shipping_address': expressDeliveryAddress,
                'billing_address': {
                    'name': 'Demo User',
                    'email': 'demo@test.com',
                    'street': 'Rue des Bourlottes 9',
                    'street2': '23',
                    'country': 'BE',
                    'city':'Ramillies',
                    'zip':'1367',
                },
            }
        ));
        const processingValues = await this.waitFor(rpc(
            this.paymentContext['transactionRoute'],
            this._prepareTransactionRouteParams(providerId),
        ));
        paymentDemoMixin.processDemoPayment(processingValues);
    },
});
