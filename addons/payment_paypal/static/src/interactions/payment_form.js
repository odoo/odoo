/* global paypal */

import { loadJS } from '@web/core/assets';
import { _t } from '@web/core/l10n/translation';
import { rpc, RPCError } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

const PAYPAL_SDK_METHODS = ['venmo', 'paypal_paylater', 'card'];
const CARD_FIELDS_STYLE = {
    "body": {
        "padding": "0",
        "border-radius": "0.4rem"
    },
    "input": {
        "font-family": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Ubuntu, "Noto Sans", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"',
        "font-size": "1rem",
        "height": "38px",
        "font-weight": "400",
        "line-height": "1.5",
        "color": "#212529",
        "background": "#FFFFFF",

        "appearance": "none",
        "-webkit-appearance": "none",
        "-moz-appearance": "none",

        "border": "1px solid color-mix(in srgb, currentcolor 15%, transparent)",
        "border-radius": "0.4rem",
        "transition": "background-color 0.05s ease-in-out, border-color 0.05s ease-in-out, box-shadow 0.05s ease-in-out"
    },
    ":focus": {
        "color": "#212529",
        "background": "#FFFFFF",
        "border": "2px solid #b8a5b3",
        "outline": "0",
        "box-shadow": "0 0 0 0.1rem rgba(113, 75, 103, 0.25)"
    },
    ".invalid": {
        "color": "#dc3545"
    }
};

patch(PaymentForm.prototype, {

    setup() {
        super.setup();
        this.paypalData = {}; // Store the component of each instantiated payment method.
        this.selectedOptionId = undefined;
    },

    // #=== DOM MANIPULATION ===#

    /**
     * @override
     */
    async willStart() {
        // Suffix the button IDs to prevent collisions when multiple button containers are present.
        const paypalEnabledButtons = [...document.querySelectorAll('#o_paypal_enabled_button')];
        const paypalDisabledButtons = [...document.querySelectorAll('#o_paypal_disabled_button')];
        paypalEnabledButtons.forEach((button, index) => button.id += `_${index}`);
        paypalDisabledButtons.forEach((button, index) => button.id += `_${index}`);

        await super.willStart(...arguments);
    },

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
            for (const buttonContainer of document.querySelectorAll('#o_paypal_button_container')) {
                buttonContainer.classList.add('d-none');
            }
        }
        await super._expandInlineForm(...arguments);
    },

    /**
     * Prepare the inline form of Paypal for direct payment.
     *
     * The PayPal SDK creates payment buttons based on the client_id and the currency of the order.
     *
     * Two payment buttons are created for each button container: one enabled and one disabled. The
     * enabled button is shown when the user is allowed to click on it, and the disabled button is
     * shown otherwise. This trick is necessary as the PayPal SDK does not provide a way to disable
     * the button after it has been created.
     *
     * The created buttons are saved and reused when switching between different payment methods to
     * avoid recreating the buttons.
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
            await super._prepareInlineForm(...arguments);
            return;
        }

        // If the selected payment method isn't handled by the Paypal SDK, hide the PayPal button so
        // the default redirect flow applies instead.
        if (!PAYPAL_SDK_METHODS.includes(paymentMethodCode)) {
            for (const buttonContainer of document.querySelectorAll('#o_paypal_button_container')) {
                buttonContainer.classList.add('d-none');
            }
            this.selectedOptionId = paymentOptionId;
            return;
        }

        this._setPaymentFlow('direct');
        const isCard = paymentMethodCode === 'card';
        const paypalLoadingList = document.querySelectorAll('#o_paypal_loading');
        if (!isCard) {
            this._hideInputs();
            for (const paypalLoading of paypalLoadingList) {
                paypalLoading.classList.remove('d-none');
            }
        }

        // Check if instantiation of the component is needed.
        if (this.selectedOptionId && this.selectedOptionId !== paymentOptionId) {
            Object.entries(this.paypalData).forEach(([_key, value]) => {
                value.enabledButtons?.forEach(btn => btn.hide());
                value.disabledButtons?.forEach(btn => btn.hide());
            });
        }
        const currentPayPalData = this.paypalData[paymentOptionId];
        if (currentPayPalData && this.selectedOptionId !== paymentOptionId) {
            const paypalSDKURL = this.paypalData[paymentOptionId]['sdkURL'];
            await this.waitFor(this._paypalLoadSDK(paypalSDKURL));
            this.paypalData[paymentOptionId]['enabledButtons']?.forEach(btn => btn.show());
            this.paypalData[paymentOptionId]['disabledButtons']?.forEach(btn => btn.show());
        }
        else if (!currentPayPalData) {
            this.paypalData[paymentOptionId] = {};
            const radio = document.querySelector('input[name="o_payment_radio"]:checked');
            let inlineFormValues;
            let paypalColor = 'default';
            if (radio) {
                inlineFormValues = JSON.parse(radio.dataset['paypalInlineFormValues']);
                paypalColor = radio.dataset['paypalColor'];
            }

            // https://developer.paypal.com/sdk/js/configuration/#link-queryparameters
            const { client_id, currency_code, country_code } = inlineFormValues;
            const paypalSDKParams = new URLSearchParams({
                "client-id": client_id,
                "components": "buttons,card-fields,payment-fields,funding-eligibility",
                "buyer-country": country_code,
                "currency": currency_code,
                "enable-funding": "paypal,paylater,venmo",
                "intent": "capture",
            });
            const paypalSDKURL = `https://www.paypal.com/sdk/js?${paypalSDKParams}`;
            this.paypalData[paymentOptionId]['sdkURL'] = paypalSDKURL;
            await this.waitFor(this._paypalLoadSDK(paypalSDKURL));

            if (isCard && paypal.CardFields !== undefined) {
                const cardFields = paypal.CardFields({
                    style: CARD_FIELDS_STYLE,
                    createOrder: () => {
                        return this.paypalData[paymentOptionId].paypalOrderId;
                    },
                    onApprove: this._paypalOnApprove.bind(this),
                });

                this.paypalData[paymentOptionId].cardFields = cardFields;

                const radio = document.querySelector('input[name="o_payment_radio"]:checked');
                const inlineForm = this._getInlineForm(radio);
                const paypalInlineForm = inlineForm.querySelector('[name="o_paypal_form"]');
                this.paypalData[paymentOptionId].inlineForm = paypalInlineForm;

                cardFields
                  .NameField({ placeholder: "" })
                  .render(inlineForm.querySelector(".paypal-card-name-field"));
                cardFields
                  .NumberField({ placeholder: "" })
                  .render(inlineForm.querySelector(".paypal-card-number-field"));
                cardFields
                  .ExpiryField({ placeholder: "" })
                  .render(inlineForm.querySelector(".paypal-card-expiry-field"));
                cardFields
                  .CVVField({ placeholder: "" })
                  .render(inlineForm.querySelector(".paypal-card-cvv-field"));
            } else {
                // Create the two sets of standard PayPal buttons.
                // See https://developer.paypal.com/sdk/js/reference.
                const METHOD_CONFIG = {
                    'paypal': {
                        fundingSource: paypal.FUNDING.PAYPAL,
                        label: 'paypal',
                        color: paypalColor
                    },
                    'paypal_paylater': {
                        fundingSource: paypal.FUNDING.PAYLATER,
                        label: 'pay',
                        color: 'gold'
                    },
                    'venmo': {
                        fundingSource: paypal.FUNDING.VENMO,
                        label: 'paypal',
                        color: 'blue'
                    },
                };
                const activeConfig = METHOD_CONFIG[paymentMethodCode] || METHOD_CONFIG['paypal'];

                this.paypalData[paymentOptionId]['enabledButtons'] = [];
                document.querySelectorAll('[id^="o_paypal_enabled_button"]').forEach(domButton => {
                    const enabledButton = paypal.Buttons({
                        fundingSource: activeConfig.fundingSource,
                        style: { // https://developer.paypal.com/sdk/js/reference/#link-style
                            layout: 'vertical',
                            label: activeConfig.label,
                            color: activeConfig.color,
                            disableMaxWidth: true,
                            borderRadius: 6,
                        },
                        createOrder: this._paypalOnClick.bind(this),
                        onApprove: this._paypalOnApprove.bind(this),
                        onCancel: this._paypalOnCancel.bind(this),
                        onError: this._paypalOnError.bind(this),
                    });
                    enabledButton.render(`#${domButton.id}`);
                    this.paypalData[paymentOptionId]['enabledButtons'].push(enabledButton);
                });

                this.paypalData[paymentOptionId]['disabledButtons'] = [];
                document.querySelectorAll('[id^="o_paypal_disabled_button"]').forEach(domButton => {
                    const disabledButton = paypal.Buttons({
                        fundingSource: activeConfig.fundingSource,
                        style: {
                            // https://developer.paypal.com/sdk/js/reference/#link-style
                            layout: "vertical",
                            color: "white",
                            label: activeConfig.label,
                            disableMaxWidth: true,
                            borderRadius: 6,
                        },
                        onInit: (data, actions) => actions.disable(), // Permanently disable the button.
                    });
                    disabledButton.render(`#${domButton.id}`);
                    this.paypalData[paymentOptionId]['disabledButtons'].push(disabledButton);
                });
            }
        }
        for (const paypalLoading of paypalLoadingList) {
            paypalLoading.classList.add('d-none');
        }
        for (const buttonContainer of document.querySelectorAll('#o_paypal_button_container')) {
            buttonContainer.classList.toggle('d-none', isCard);
        }
        this.selectedOptionId = paymentOptionId;
    },

    /**
     * Load the JS from the PayPal SDK URL and set an identifier dedicated to Odoo, for PayPal to be
     * able to recognize which transactions are originating from Odoo.
     *
     * @private
     * @param {string} paypalSDKURL - The SDK URL that needs to be loaded on the page.
     * @return {void}
     */
    async _paypalLoadSDK(paypalSDKURL) {
        await loadJS(paypalSDKURL);
        const paypalSDKs = document.querySelectorAll(`script[src="${paypalSDKURL}"]`);
        [...paypalSDKs].forEach(sdk => {
            sdk.setAttribute('data-partner-attribution-id', 'ODOO_SP_DIRECT');
        });
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Handle the click event of the component and initiate the payment.
     *
     * @private
     * @return {void}
     */
    async _paypalOnClick() {
        await this.waitFor(this.submitForm(new Event("PayPalClickEvent")));
        return this.paypalData[this.selectedOptionId].paypalOrderId;
    },

    _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'paypal') {
            super._processDirectFlow(...arguments);
            return;
        }
        this.paypalData[paymentOptionId].paypalOrderId = processingValues['order_id'];
        this.paypalData[paymentOptionId].paypalTxRef = processingValues['reference'];

        if (paymentMethodCode === 'card') {
            const currentPayPalData = this.paypalData[paymentOptionId];
            if (currentPayPalData && currentPayPalData.cardFields) {
                currentPayPalData.cardFields.submit().catch((error) => {
                    this._displayErrorDialog("Validation Error", error.message);
                    this._enableButton();
                });
            }
        }
    },

    /**
     * Handle the approval event of the component and complete the payment.
     *
     * @private
     * @param {object} data - The data returned by PayPal on approving the order.
     * @return {void}
     */
    async _paypalOnApprove(data) {
        const orderID = data.orderID;
        try {
            await this.waitFor(rpc('/payment/paypal/complete_order', {
                'order_id': orderID,
                'reference': this.paypalData[this.selectedOptionId].paypalTxRef,
            }));
            // Close the PayPal buttons that were rendered
            const enabledButtons = this.paypalData[this.selectedOptionId]['enabledButtons'];
            if (enabledButtons) {
                for (const enabledButton of enabledButtons) {
                    enabledButton.close();
                }

            }
            window.location = '/payment/status';
        } catch (error) {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            }
            return Promise.reject(error);
        }
    },

    /**
     * Handle the cancel event of the component.
     * @private
     * @return {void}
     */
    _paypalOnCancel() {
        this._enableButton();
    },

    /**
     * Handle the error event of the component.
     * @private
     * @param {object} error - The error in the component.
     * @return {void}
     */
    _paypalOnError(error) {
        const message = error.message;
        this._enableButton();
        // Paypal throws an error if the popup is closed before it can load;
        // this case should be treated as an onCancel event.
        if (message !== "Detected popup close" && !(error instanceof RPCError)) {
            this._displayErrorDialog(_t("Payment processing failed"), message);
        }
    },
});
