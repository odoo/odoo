import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

const LOYALTY_PROVIDER_CODES = ['gift_card', 'ewallet'];

patch(PaymentForm.prototype, {

    setup() {
        super.setup();
        Object.assign(this.dynamicContent, {
            '[name="o_loyalty_gift_card_apply"]': { 't-on-click': this.applyGiftCard },
            '[name="o_loyalty_gift_card_code"]': { 't-on-keydown': this.onGiftCardCodeKeydown },
            '[name="o_loyalty_card_select"]': {
                't-on-change': this.selectLoyaltyCard,
                't-on-click': (ev) => ev.stopPropagation(), // Don't toggle the radio.
            },
        });
    },

    // #=== EVENT HANDLERS ===#

    /**
     * Check the gift card code and display the amount it covers.
     *
     * @param {Event} ev
     * @return {void}
     */
    async applyGiftCard(ev) {
        ev.preventDefault();
        const option = ev.currentTarget.closest('[name="o_payment_option"]');
        const radio = option.querySelector('input[name="o_payment_radio"]');
        const codeInput = option.querySelector('[name="o_loyalty_gift_card_code"]');
        const errorContainer = option.querySelector('[name="o_loyalty_gift_card_error"]');
        errorContainer.classList.add('d-none');
        if (!codeInput.value.trim()) {
            return;
        }
        const result = await this.waitFor(rpc('/payment/loyalty/check_card', {
            provider_id: this._getProviderId(radio),
            code: codeInput.value,
            amount: this.paymentContext.amount,
            currency_id: this.paymentContext.currencyId,
        }));
        if (result.error) {
            errorContainer.textContent = result.error;
            errorContainer.classList.remove('d-none');
            this._setLoyaltyCard(radio, {});
        } else {
            codeInput.value = '';
            this._setLoyaltyCard(radio, result);
        }
        this._adaptSubmitButtonLabel(this._getPaymentMethodCode(radio));
    },

    /**
     * Apply the gift card code when the customer presses Enter instead of submitting the form.
     *
     * @param {KeyboardEvent} ev
     * @return {void}
     */
    onGiftCardCodeKeydown(ev) {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            ev.stopPropagation();
            ev.currentTarget.closest('[name="o_payment_option"]')
                .querySelector('[name="o_loyalty_gift_card_apply"]').click();
        }
    },

    /**
     * Update the amount to pay when the customer selects another eWallet.
     *
     * @param {Event} ev
     * @return {void}
     */
    selectLoyaltyCard(ev) {
        const select = ev.currentTarget;
        const radio = select.closest('[name="o_payment_option"]')
            .querySelector('input[name="o_payment_radio"]');
        const option = select.selectedOptions[0];
        this._setLoyaltyCard(radio, {
            card_id: select.value,
            amount: option.dataset.amount,
            amount_formatted: option.dataset.amountFormatted,
        });
        this._adaptSubmitButtonLabel(this._getPaymentMethodCode(radio));
    },

    /**
     * Prevent paying with a loyalty provider without a card.
     *
     * @override
     */
    async submitForm(ev) {
        const checkedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');
        if (
            checkedRadio
            && this._isLoyaltyProvider(this._getProviderCode(checkedRadio))
            && !this._getLoyaltyInfo(checkedRadio)?.dataset.cardId
        ) {
            ev.stopPropagation();
            ev.preventDefault();
            this._displayErrorDialog(
                _t("No card selected"), _t("Please apply a gift card code before paying.")
            );
            return;
        }
        return super.submitForm(...arguments);
    },

    // #=== DOM MANIPULATION ===#

    /**
     * Use the direct flow for loyalty providers: the transaction is processed at its creation.
     *
     * @override
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (!this._isLoyaltyProvider(providerCode)) {
            await super._prepareInlineForm(...arguments);
            return;
        }
        this._setPaymentFlow('direct');
    },

    /**
     * Show the amount paid with the selected card in the submit button.
     *
     * @override
     */
    _adaptSubmitButtonLabel(paymentMethodCode) {
        super._adaptSubmitButtonLabel(...arguments);
        const checkedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');
        const loyaltyInfo = checkedRadio && this._isLoyaltyProvider(
            this._getProviderCode(checkedRadio)
        ) && this._getLoyaltyInfo(checkedRadio);
        const amountLabel = loyaltyInfo?.dataset.cardId ? loyaltyInfo.dataset.amountFormatted : '';
        document.querySelectorAll('button[name="o_payment_submit_button"]').forEach(btn => {
            const payNowLabel = btn.querySelector('[name="o_pay_now_label"]');
            if (!payNowLabel) {
                return;
            }
            let amountSpan = btn.querySelector('[name="o_loyalty_pay_amount"]');
            if (!amountSpan) {
                amountSpan = document.createElement('span');
                amountSpan.setAttribute('name', 'o_loyalty_pay_amount');
                payNowLabel.after(amountSpan);
            }
            amountSpan.textContent = amountLabel ? ` - ${amountLabel}` : '';
        });
    },

    /**
     * Store the card to pay with and display the amount it covers.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button of the loyalty payment method.
     * @param {object} cardValues - The id, code, and amount of the card.
     * @return {void}
     */
    _setLoyaltyCard(radio, { card_id, code, amount, amount_formatted }) {
        const loyaltyInfo = this._getLoyaltyInfo(radio);
        loyaltyInfo.dataset.cardId = card_id ?? '';
        loyaltyInfo.dataset.amount = amount ?? '';
        loyaltyInfo.dataset.amountFormatted = amount_formatted ?? '';
        const codeSpan = loyaltyInfo.querySelector('[name="o_loyalty_card_code"]');
        if (codeSpan && code !== undefined) {
            codeSpan.textContent = code;
        }
        loyaltyInfo.querySelector('[name="o_loyalty_amount"]').textContent = amount_formatted ?? '';
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Pay with the card selected for the loyalty provider, and only up to its balance.
     *
     * @override
     */
    _prepareTransactionRouteParams() {
        const params = super._prepareTransactionRouteParams(...arguments);
        if (this._isLoyaltyProvider(this.paymentContext.providerCode)) {
            const checkedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');
            const loyaltyInfo = this._getLoyaltyInfo(checkedRadio);
            params.loyalty_card_id = parseInt(loyaltyInfo.dataset.cardId);
            params.amount = parseFloat(loyaltyInfo.dataset.amount);
        }
        return params;
    },

    /**
     * Redirect to the status page; loyalty transactions are processed at their creation.
     *
     * @override
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (!this._isLoyaltyProvider(providerCode)) {
            await super._processDirectFlow(...arguments);
            return;
        }
        window.location = '/payment/status';
    },

    // #=== GETTERS ===#

    _isLoyaltyProvider(providerCode) {
        return LOYALTY_PROVIDER_CODES.includes(providerCode);
    },

    _getLoyaltyInfo(radio) {
        return radio.closest('[name="o_payment_option"]')
            ?.querySelector('[name="o_loyalty_payment_info"]');
    },

});
