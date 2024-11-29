import paymentForm from '@payment/js/payment_form';
import { _t } from '@web/core/l10n/translation';
import { pyToJsLocale } from '@web/core/l10n/utils';
import { rpc, RPCError } from '@web/core/network/rpc';

paymentForm.include({

    mercadoPagoCheckout: undefined,
    mercadoPagoComponents: undefined,

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of Adyen for direct payment.
     *
     * @override method from payment.payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'mercado_pago') {
            this._super(...arguments);
            return;
        }

        // Check if instantiation of the component is needed.
        this.mercadoPagoComponents ??= {}; // Store the component of each instantiated payment method.
        if (flow === 'token') {
            return; // No component for tokens.
        } else if (this.mercadoPagoComponents[paymentOptionId]) {
            this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation.
            return; // Don't re-instantiate if already done for this payment method.
        }

        // Overwrite the flow of the selected payment method.
        this._setPaymentFlow('direct');

        // Extract and deserialize the inline form values.
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineFormValues = JSON.parse(radio.dataset['mercadoPagoInlineFormValues']);
        const formattedAmount = inlineFormValues['formatted_amount'];

        // Create the checkout object if not already done for another payment method.
        if (!this.mercadoPagoCheckout) {
            try {
                const mp = new MercadoPago('TEST-6195235198398424-061413-5b6a279b4105ee38995de109e8e8d9b1-1074382083', {
                locale: 'en'
                });
                // Await the RPC to let it create AdyenCheckout before using it.
                // Create the Adyen Checkout SDK.
                const providerState = this._getProviderState(radio);
                const settings = {
                    paymentMethodsResponse: response,
                    clientKey: inlineFormValues['client_key'],
                    amount: formattedAmount,
                    locale: pyToJsLocale(this._getContext().lang) || 'en-US',
                    environment: providerState === 'enabled' ? 'live' : 'test',
                    onAdditionalDetails: this._adyenOnSubmitAdditionalDetails.bind(this),
                    onError: this._adyenOnError.bind(this),
                    onSubmit: this._adyenOnSubmit.bind(this),
                    paymentMethodsConfiguration: {
                        card: {hasHolderName: true, holderNameRequired: true},
                    }
                };
                this.adyenCheckout = await AdyenCheckout(configuration);
            } catch (error) {
                if (error instanceof RPCError) {
                    this._displayErrorDialog(
                        _t("Cannot display the payment form"), error.data.message
                    );
                    this._enableButton();
                    return;
                }
                else {
                    return Promise.reject(error);
                }
            }
        }

        // Instantiate and mount the component.
        const componentConfiguration = {
            showBrandsUnderCardNumber: false,
            showPayButton: false,
            billingAddressRequired: false, // The billing address is included in the request.
        };
        if (paymentMethodCode === 'card') {
            // Forbid Bancontact cards in the card component.
            componentConfiguration['brands'] = ['mc', 'visa', 'amex', 'discover'];
        }
        else if (paymentMethodCode === 'paypal') {
            // PayPal requires the form to be submitted with its own button.
            Object.assign(componentConfiguration, {
                style: {
                    disableMaxWidth: true
                },
                showPayButton: true,
                blockPayPalCreditButton: true,
                blockPayPalPayLaterButton: true
            });
            this._hideInputs();
            // Define necessary fields as the step _submitForm is missed.
            Object.assign(this.paymentContext, {
                tokenizationRequested: false,
                providerId: providerId,
                paymentMethodId: paymentOptionId,
            });
        }
        const inlineForm = this._getInlineForm(radio);
        const adyenContainer = inlineForm.querySelector('[name="o_adyen_component_container"]');
        this.adyenComponents[paymentOptionId] = this.adyenCheckout.create(
            inlineFormValues['adyen_pm_code'], componentConfiguration
        ).mount(adyenContainer);
    },
});
