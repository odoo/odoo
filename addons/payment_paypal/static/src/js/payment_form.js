/* global paypal */

import { loadJS } from '@web/core/assets';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';

import paymentForm from '@payment/js/payment_form';

paymentForm.include({
    inlineFormValues: undefined,
    paypalColor: 'blue',
    selectedOptionId: undefined,
    paypalData: undefined,

    // #=== DOM MANIPULATION ===#

    /**
     * Hides paypal button container if the expanded inline form is another provider.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the payment option.
     * @return {void}
     */
    async _expandInlineForm(radio) {
        const providerCode = this._getProviderCode(radio);
        if (providerCode !== 'paypal') {
            document.getElementById('o_paypal_button').classList.add('d-none');
        }
        this._super(...arguments);
    },
    /**
     * Prepare the inline form of Paypal for direct payment.
     * The PayPal sdk creates the payment button based on the client_id
     * and the currency of the order.
     * The created button is saved and reused when switching between different payment methods,
     * to avoid recreating the buttons.
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
        }

        this._hideInputs();
        this._setPaymentFlow('direct');
        document.getElementById('o_paypal_button').classList.remove('d-none');
        document.getElementById('o_paypal_loading').classList.remove('d-none');
        // Check if instantiation of the component is needed.
        this.paypalData ??= {}; // Store the component of each instantiated payment method.
        const currentPayPalData = this.paypalData[paymentOptionId]
        if (this.selectedOptionId && this.selectedOptionId !== paymentOptionId) {
            this.paypalData[this.selectedOptionId]['paypalButton'].hide()
        }
        if (currentPayPalData && this.selectedOptionId !== paymentOptionId) {
            const paypalSDKURL = this.paypalData[paymentOptionId]['sdkURL']
            const paypalButton = this.paypalData[paymentOptionId]['paypalButton']
            await loadJS(paypalSDKURL);
            paypalButton.show();
        }
        else if (!currentPayPalData) {
            this.paypalData[paymentOptionId] = {}
            const radio = document.querySelector('input[name="o_payment_radio"]:checked');
            if (radio) {
                this.inlineFormValues = JSON.parse(radio.dataset['paypalInlineFormValues']);
                this.paypalColor = radio.dataset['paypalColor']
            }

            // https://developer.paypal.com/sdk/js/configuration/#link-queryparameters
            const { client_id, currency_code } = this.inlineFormValues
            const paypalSDKURL = `https://www.paypal.com/sdk/js?client-id=${
                client_id}&components=buttons&currency=${currency_code}&intent=capture`
            await loadJS(paypalSDKURL);
            const paypalButton = paypal.Buttons({ // https://developer.paypal.com/sdk/js/reference
                fundingSource: paypal.FUNDING.PAYPAL,
                style: { // https://developer.paypal.com/sdk/js/reference/#link-style
                    color: this.paypalColor,
                    label: 'paypal',
                    disableMaxWidth: true,
                    borderRadius: 6,
                },
                createOrder: this._paypalOnClick.bind(this),
                onApprove: this._paypalOnApprove.bind(this),
                onCancel: this._paypalOnCancel.bind(this),
                onError: this._paypalOnError.bind(this),
            });
            this.paypalData[paymentOptionId]['sdkURL'] = paypalSDKURL;
            this.paypalData[paymentOptionId]['paypalButton'] = paypalButton;
            paypalButton.render('#o_paypal_button');
        }
        document.getElementById('o_paypal_loading').classList.add('d-none');
        this.selectedOptionId = paymentOptionId;
    },
    // #=== PAYMENT FLOW ===#

    /**
     * Handle the click event of the component and initiate the payment.
     *
     * @private
     * @return {void}
     */
    async _paypalOnClick() {
        await this._submitForm(new Event("PayPalClickEvent"));
        return this.paypalData[this.selectedOptionId].paypalOrderId;
    },

    _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'paypal') {
            this._super(...arguments);
            return;
        }
        this.paypalData[paymentOptionId].paypalOrderId = processingValues['order_id'];
    },

    /**
     * Handle the approval event of the component and complete the payment.
     *
     * @private
     * @param {object} data - The data returned by PayPal on approving the order.
     * @return {void}
     */
    _paypalOnApprove(data) {
        const orderID = data.orderID;
        const { provider_id } = this.inlineFormValues

        rpc('/payment/paypal/complete_order', {
            'provider_id': provider_id,
            'order_id': orderID,
        }).then(() => {
            // Close the PayPal buttons that were rendered
            this.paypalData[this.selectedOptionId]['paypalButton'].close();
            window.location = '/payment/status';
        })
    },

    /**
     * Handle the cancel event of the component.
     * @private
     * @return {void}
     */
    _paypalOnCancel() {
        this.call('ui', 'unblock');
    },

    /**
     * Handle the error event of the component.
     * @private
     * @param {object} error - The error in the component.
     * @return {void}
     */
    _paypalOnError(error) {
        const message = error.message
        this.call('ui', 'unblock');
        // Paypal throws an error if the popup is closed before it can load;
        // this case should be treated as an onCancel event.
        if (message !== "Detected popup close") {
            this._displayErrorDialog(_t("Payment processing failed"), error.message);
        }
    },
});
