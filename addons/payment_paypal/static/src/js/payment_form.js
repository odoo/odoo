/* global paypal */

import { loadJS } from '@web/core/assets';
import { _t } from '@web/core/l10n/translation';
import { rpc, RPCError } from '@web/core/network/rpc';

import paymentForm from '@payment/js/payment_form';

paymentForm.include({
    selectedOptionId: undefined,
    paypalData: undefined,

    // #=== DOM MANIPULATION ===#

    /**
     * Deactivate duplicated PayPal button containers from the DOM.
     * This is necessary as the PayPal button cannot be rendered twice in the same DOM.
     */
    _cleanDuplicatedPaypalContainers() {
        // Find all PayPal button containers as it might be duplicated in the DOM.
        const containers = [...document.querySelectorAll('[id^="o_paypal_button_container"]')];
        let isDomModified = false;
        let tempContainer;

        // If a PayPal button container is found save it and empty it
        containers.forEach(container => {
            if (container.querySelectorAll('[id^="zoid-paypal-buttons"]').length > 0) {
                tempContainer = container.cloneNode(true);
            }
        });

        containers.forEach(container => {
            const isInvisible = container.offsetParent === null &&
                !container.classList.contains('d-none');
            const isInactive = container.id.endsWith('_inactive');
            if (isInvisible && !isInactive) {
                container.innerHTML = '';
                container.id += '_inactive';
            } else if (!isInvisible && isInactive) {
                container.id = container.id.replace('_inactive', '');
                isDomModified = true;
            }
        });

        let activeContainer = document.getElementById('o_paypal_button_container');
        if (isDomModified && tempContainer && activeContainer) {
            while (activeContainer.firstChild) {
                activeContainer.removeChild(activeContainer.firstChild);
            }
            [...tempContainer.childNodes].forEach((child) => {
                activeContainer.appendChild(child.cloneNode(true));
            });
        }

        return isDomModified;
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
            document.getElementById('o_paypal_button_container').classList.add('d-none');
        }
        this._super(...arguments);
    },

    /**
     * Prepare the inline form of Paypal for direct payment.
     *
     * The PayPal SDK creates payment buttons based on the client_id and the currency of the order.
     *
     * Two payment buttons are created: one enabled and one disabled. The enabled button is shown
     * when the user is allowed to click on it, and the disabled button is shown otherwise. This
     * trick is necessary as the PayPal SDK does not provide a way to disable the button after it
     * has been created.
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
            this._super(...arguments);
            return;
        }

        this._hideInputs();
        this._setPaymentFlow('direct');
        // Necessary for edit mode and some use cases like tablet orientation changes.
        if (!this._mobileDesktopToggleListener) {
            window.addEventListener("resize", () => this._prepareInlineForm(...arguments));
            this._mobileDesktopToggleListener = true;
        }
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        let isDomModified = false;
        if (radio && radio.getAttribute('data-provider-code') === providerCode) {
            isDomModified = this._cleanDuplicatedPaypalContainers();
        }
        document.getElementById('o_paypal_loading').classList.remove('d-none');
        // Check if instantiation of the component is needed.
        this.paypalData ??= {}; // Store the component of each instantiated payment method.
        if (this.selectedOptionId && this.selectedOptionId !== paymentOptionId) {
            this.paypalData[this.selectedOptionId]['enabledButton'].hide()
            this.paypalData[this.selectedOptionId]['disabledButton'].hide()
        }
        const currentPayPalData = this.paypalData[paymentOptionId]
        if (currentPayPalData && this.selectedOptionId !== paymentOptionId) {
            const paypalSDKURL = this.paypalData[paymentOptionId]['sdkURL']
            const enabledButton = this.paypalData[paymentOptionId]['enabledButton']
            const disabledButton = this.paypalData[paymentOptionId]['disabledButton']
            await loadJS(paypalSDKURL);
            enabledButton.show();
            disabledButton.show();
        }
        else if (!currentPayPalData || isDomModified) {
            this.paypalData[paymentOptionId] = {}
            let inlineFormValues
            let paypalColor = 'blue'
            if (radio) {
                inlineFormValues = JSON.parse(radio.dataset['paypalInlineFormValues']);
                paypalColor = radio.dataset['paypalColor']
            }

            // https://developer.paypal.com/sdk/js/configuration/#link-queryparameters
            const { client_id, currency_code } = inlineFormValues
            const paypalSDKURL = `https://www.paypal.com/sdk/js?client-id=${
                client_id}&components=buttons&currency=${currency_code}&intent=capture`
            this.paypalData[paymentOptionId]['sdkURL'] = paypalSDKURL;
            await loadJS(paypalSDKURL);

            // Create the two PayPal buttons. See https://developer.paypal.com/sdk/js/reference.
            const enabledButton = paypal.Buttons({
                fundingSource: paypal.FUNDING.PAYPAL,
                style: { // https://developer.paypal.com/sdk/js/reference/#link-style
                    color: paypalColor,
                    label: 'paypal',
                    disableMaxWidth: true,
                    borderRadius: 6,
                },
                createOrder: this._paypalOnClick.bind(this),
                onApprove: this._paypalOnApprove.bind(this),
                onCancel: this._paypalOnCancel.bind(this),
                onError: this._paypalOnError.bind(this),
            });
            enabledButton.render('#o_paypal_button_container #o_paypal_enabled_button');
            this.paypalData[paymentOptionId]['enabledButton'] = enabledButton;

            const disabledButton = paypal.Buttons({
                fundingSource: paypal.FUNDING.PAYPAL,
                style: { // https://developer.paypal.com/sdk/js/reference/#link-style
                    color: 'silver',
                    label: 'paypal',
                    disableMaxWidth: true,
                    borderRadius: 6,
                },
                onInit: (data, actions) => actions.disable(),  // Permanently disable the button.
            });
            disabledButton.render('#o_paypal_button_container #o_paypal_disabled_button');
            this.paypalData[paymentOptionId]['disabledButton'] = disabledButton;
        }

        const paymentButton = document.getElementById('o_paypal_button_container');
        // Remove all rendered PayPal buttons except the last one to avoid duplicates.
        if (paymentButton && paymentButton.children.length > 0) {
            [...paymentButton.children].forEach((child) => {
                const children = [...child.querySelectorAll('[id^="zoid-paypal-buttons-uid"]')]
                children.forEach((el, index) => {
                    if (index < children.length - 1) {
                        el.remove();
                    }
                });
            });
        }
        document.getElementById('o_paypal_loading').classList.add('d-none');
        paymentButton.classList.remove('d-none');
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
        this.paypalData[paymentOptionId].paypalTxRef = processingValues['reference'];
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

        await rpc('/payment/paypal/complete_order', {
            'order_id': orderID,
            'reference': this.paypalData[this.selectedOptionId].paypalTxRef,
        }).then(() => {
            // Close the PayPal buttons that were rendered
            this.paypalData[this.selectedOptionId]['enabledButton'].close();
            window.location = '/payment/status';
        }).catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            }
            return Promise.reject(error);
        })
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
        const message = error.message
        this._enableButton();
        // Paypal throws an error if the popup is closed before it can load;
        // this case should be treated as an onCancel event.
        if (message !== "Detected popup close" && !(error instanceof RPCError)) {
            this._displayErrorDialog(_t("Payment processing failed"), message);
        }
    },
});
