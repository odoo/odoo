import { usePlugin, markup } from '@odoo/owl';
import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { redirect } from '@web/core/utils/urls';
import { setElementContent } from '@web/core/utils/html';
import { BootstrapInstance } from '@web/core/utils/bootstrap_plugin';
import wSaleUtils from '@website_sale/js/website_sale_utils';

export class Checkout extends Interaction {
    static selector = '#shop_checkout';
    dynamicContent = {
        // Addresses
        '.card': { 't-on-click': this.changeAddress },
        // Open the edit dialog instead of letting the pencil link navigate away.
        '.js_edit_address': { 't-on-click.stop': this.openEditAddressDialog },
        '#o_wsale_edit_address_modal_save': { 't-on-click': this.saveEditAddressDialog },
        '#use_delivery_as_billing': { 't-on-change': this.toggleBillingAddressRow },
        // Delivery methods
        '[name="o_delivery_radio"]': { 't-on-click': this.selectDeliveryMethod },
        // Address form (new customers filling in their details inline on this page): refresh the
        // delivery methods as soon as enough of the address is known to compute them.
        'form.address_autoformat select[name="country_id"]': {
            't-on-change': this.debounced(this.updateDeliveryAddress, 500),
        },
        'form.address_autoformat select[name="state_id"]': {
            't-on-change': this.updateDeliveryAddress,
        },
        'form.address_autoformat input[name="zip"]': {
            't-on-input': this.debounced(this.updateDeliveryAddress, 500),
        },
    };

    setup() {
        // There are two main buttons in the DOM (one for mobile and one for desktop).
        // We need to get the one that's actually displayed.
        this.mainButton = Array.from(document.getElementsByName('website_sale_main_button'))
            .find(button => button.offsetParent !== null);
        this.useDeliveryAsBillingToggle = document.querySelector('#use_delivery_as_billing');
        this.billingContainer = this.el.querySelector('#billing_container');
        this.vatDiv = this.el.querySelector(".o_address_card_vat");
        this.addBillingAddressBtn = this.el.querySelector('.o_add_billing_address_btn');
        this.bootstrap = usePlugin(BootstrapInstance);
        this.editAddressModalEl = this.el.querySelector('#o_wsale_edit_address_modal');
    }

    async willStart() {
        await this.waitFor(this._prepareDeliveryMethods());
    }

    async start() {
        // Monitor when the page is restored from the bfcache.
        const boundOnNavigationBack = this._onNavigationBack.bind(this);
        window.addEventListener("pageshow", boundOnNavigationBack);
        this.registerCleanup(() => window.removeEventListener("pageshow", boundOnNavigationBack));
    }

    /**
     * Reload the page when the page is restored from the bfcache.
     *
     * @param {PageTransitionEvent} event - The pageshow event.
     * @private
     */
    _onNavigationBack(event) {
        if (event.persisted) {
            window.location.reload();
        }
    }

    /**
     * Set the billing or delivery address on the order and update the corresponding card.
     *
     * @param {Event} ev
     * @return {void}
     */
    async changeAddress(ev) {
        const newAddress = ev.currentTarget;
        if (newAddress.classList.contains('bg-400')) { // If the card is already selected.
            return;
        }
        const addressType = newAddress.dataset.addressType;

        // Remove the highlighting from the previously selected address card.
        const previousAddress = this._getSelectedAddress(addressType);
        this._tuneDownAddressCard(previousAddress);

        // Highlight the newly selected address card.
        this._highlightAddressCard(newAddress);
        const selectedPartnerId = newAddress.dataset.partnerId;
        await this.waitFor(this.updateAddress(addressType, selectedPartnerId));
        // A delivery address is changed.
        if (addressType === 'delivery') {
            if (this.useDeliveryAsBillingToggle?.checked) {
                this._selectMatchingBillingAddressCard(selectedPartnerId);
            }
            const deliveryFormHtml = await this.waitFor(rpc('/shop/delivery_methods'));
            // The delivery methods are regenerated below, so we need to stop and start interactions
            // to make sure the regenerated delivery methods are properly handled.
            this.services['public.interactions'].stopInteractions(this.el);
            // Update the available delivery methods.
            document.getElementById('o_delivery_form').innerHTML = deliveryFormHtml;
            this.services['public.interactions'].startInteractions(this.el);
            await this.waitFor(this._prepareDeliveryMethods());
        }
        this._enableMainButton();  // Try to enable the main button.
    }

    /**
     * Show/hide the billing address row when the user toggles the 'use delivery as billing' input.
     *
     * The URLs of the "create address" buttons are updated to propagate the value of the input.
     *
     * @param ev
     * @return {void}
     */
    async toggleBillingAddressRow(ev) {
        const useDeliveryAsBilling = ev.target.checked;

        const addDeliveryAddressButton = this.el.querySelector(
            '.o_address_card_add_new[data-address-type="delivery"]'
        );
        if (addDeliveryAddressButton) {  // If `Add` button for delivery.
            // Update the `use_delivery_as_billing` query param for a new delivery address URL.
            const addDeliveryUrl = new URL(addDeliveryAddressButton.href);
            addDeliveryUrl.searchParams.set(
                'use_delivery_as_billing', encodeURIComponent(useDeliveryAsBilling)
            );
            addDeliveryAddressButton.href = addDeliveryUrl.toString();
        }

        // Toggle the billing address row.
        if (useDeliveryAsBilling) {
            this.billingContainer.classList.add('d-none');  // Hide the billing address row.
            this.vatDiv?.classList.remove("d-none");  // Show the VAT field in address cards.
            const selectedDeliveryAddress = this._getSelectedAddress('delivery');
            this._selectMatchingBillingAddressCard(selectedDeliveryAddress.dataset.partnerId)
            await this.waitFor(
                this.updateAddress('billing', selectedDeliveryAddress.dataset.partnerId)
            );
        } else {
            this._disableMainButton();
            this.billingContainer.classList.remove('d-none'); // Show the billing address row.
            this.vatDiv?.classList.add("d-none");  // Hide the VAT field in address cards.

        }
        this.addBillingAddressBtn.classList.toggle('d-none', useDeliveryAsBilling);

        this._enableMainButton();  // Try to enable the main button.
    }

    /**
     * Fetch the delivery rate for the selected delivery method and update the displayed amounts.
     *
     * @param {Event} ev
     * @return {void}
     */
    async selectDeliveryMethod(ev) {
        const checkedRadio = ev.currentTarget;
        if (checkedRadio.disabled) {  // The delivery rate request failed.
            return; // Failing delivery methods cannot be selected.
        }

        // Disable the main button while fetching delivery rates.
        this._disableMainButton();

        // Fetch delivery rates and update the cart summary and the price badge accordingly.
        await this.waitFor(this._updateDeliveryMethod(checkedRadio));

        // Re-enable the main button after delivery rates have been fetched.
        this._enableMainButton();
    }

    /**
     * Push the partial address (country/state/zip) currently typed in the inline address form to
     * the server, and refresh the delivery methods so that address-dependent carriers (e.g.
     * country-restricted ones) unlock without waiting for the form to be submitted.
     *
     * @return {void}
     */
    async updateDeliveryAddress() {
        const addressForm = this.el.querySelector('form.address_autoformat');
        if (!addressForm) {
            return; // No inline address form on this page (the address is already known).
        }

        this._disableMainButton();
        const deliveryFormHtml = await this.waitFor(rpc('/shop/checkout/update_delivery_address', {
            country_id: addressForm.country_id?.value,
            state_id: addressForm.state_id?.value,
            zip: addressForm.zip?.value,
        }));
        if (deliveryFormHtml) {
            // The delivery methods are regenerated below, so we need to stop and start
            // interactions to make sure the regenerated delivery methods are properly handled.
            this.services['public.interactions'].stopInteractions(this.el);
            document.getElementById('o_delivery_form').innerHTML = deliveryFormHtml;
            this.services['public.interactions'].startInteractions(this.el);
            await this.waitFor(this._prepareDeliveryMethods());
        }
        this._enableMainButton();
    }

    // #=== DOM MANIPULATION ===#

    /**
     * Remove the highlighting from the address card.
     *
     * @private
     * @param card - The card element of the selected address.
     * @return {void}
     */
    _tuneDownAddressCard(card) {
        if (!card) return;
        card.classList.remove('bg-400', 'border', 'border-primary');
    }

    /**
     * Highlight the address card.
     *
     * @private
     * @param card - The card element of the selected address.
     * @return {void}
     */
    _highlightAddressCard(card) {
        if (!card) return;
        card.classList.add('bg-400', 'border', 'border-primary');
    }

    /**
     * Disable the main button.
     *
     * @private
     * @return {void}
     */
    _disableMainButton() {
        this.mainButton?.classList.add('disabled');
    }

    /**
     * Enable the main button if all conditions are satisfied.
     *
     * @private
     * @return {void}
     */
    _enableMainButton() {
        if (this._canEnableMainButton()) {
            this.mainButton?.classList.remove('disabled');
        }
    }

    /**
     * Return whether a delivery method and a billing address are selected.
     *
     * @private
     * @return {boolean}
     */
    _canEnableMainButton(){
        return this._isDeliveryMethodReady() && this._isBillingAddressSelected();
    }

    /**
     * Set the delivery method on the order and update the price badge and cart summary.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {void}
     */
    async _updateDeliveryMethod(radio) {
        this._showLoadingBadge(radio);
        const result = await this.waitFor(this._setDeliveryMethod(radio.dataset.dmId));
        this._updateAmountBadge(radio, result);
        this._updateCartSummaries(result);
        if (result.shipping_tracking_info) {
            wSaleUtils.dispatchTrackingEvent(
                "add_shipping_info_event", result.shipping_tracking_info,
            );
        }
    }

    /**
     * Display a loading spinner on the delivery price badge.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {void}
     */
    _showLoadingBadge(radio) {
        const deliveryPriceBadge = this._getDeliveryPriceBadge(radio);
        this._clearElement(deliveryPriceBadge);
        deliveryPriceBadge.appendChild(this._createLoadingElement());
    }

    /**
     * Update the delivery price badge with the delivery rate.
     *
     * If the rate is zero, the price badge displays "Free" instead.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @param {Object} rateData - The delivery rate data.
     * @return {void}
     */
    _updateAmountBadge(radio, rateData) {
        const deliveryPriceBadge = this._getDeliveryPriceBadge(radio);
        if (rateData.success) {
            if (rateData.compute_price_after_delivery) {
                // Inform the customer that the price will be computed after delivery.
                deliveryPriceBadge.textContent = _t("Computed after delivery");
            } else if (rateData.is_free_delivery) {
                // If it's a free delivery (`free_over` field), show 'Free', not '$ 0'.
                deliveryPriceBadge.textContent = _t("Free");
            } else {
                deliveryPriceBadge.innerHTML = rateData.amount_delivery;
            }
            this._toggleDeliveryMethodRadio(radio);
        } else {
            deliveryPriceBadge.textContent = rateData.error_message;
            this._toggleDeliveryMethodRadio(radio, true);
        }
    }

    /**
     * Update the order summary table with the delivery rate of the selected delivery method.
     *
     * @private
     * @param {Object} result - The order summary values.
     * @param {Object} targetEl - Specific cart summary to update.
     * @return {void}
     */
    _updateCartSummary(result, targetEl) {
        const amountDelivery = targetEl.querySelector(
            'tr[name="o_order_delivery"] .monetary_field'
        );
        const amountUntaxed = targetEl.querySelector(
            'tr[name="o_order_total_untaxed"] .monetary_field'
        );
        const amountTax = targetEl.querySelector('#order_tax_lines_container');
        const amountTotal = targetEl.parentElement.querySelectorAll(
            'tr[name="o_order_total"] .monetary_field, #amount_total_summary.monetary_field'
        );

        // When no dm is set and a price span is hidden, hide the message and show the price span.
        if (amountDelivery.classList.contains('d-none')) {
            amountDelivery.querySelector('span[name="o_message_no_dm_set"]')?.classList.add('d-none');
            amountDelivery.classList.remove('d-none');
        }
        amountDelivery.innerHTML = result.amount_delivery;
        if (amountUntaxed) {
            setElementContent(amountUntaxed, markup(result.amount_untaxed));
        }
        amountTax.outerHTML = result.amount_tax_lines;
        amountTotal.forEach(total => total.innerHTML = result.amount_total);
    }

    /**
     * Update the order summary table with the delivery rate of the selected delivery method.
     *
     * @private
     * @param {Object} result - The order summary values.
     * @return {void}
     */
    _updateCartSummaries(result) {
        const parentElements = document.querySelectorAll(
            '#o_cart_summary_offcanvas, div.o_total_card'
        );
        parentElements.forEach(el => this._updateCartSummary(result, el));
    }

    /**
     * Enable or disable radio selection for a delivery method.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @param {Boolean} disable - Whether the radio should be disabled.
     */
    _toggleDeliveryMethodRadio(radio, disable=false) {
        const deliveryPriceBadge = this._getDeliveryPriceBadge(radio);
        radio.disabled = disable;
        if (disable) {
            deliveryPriceBadge.classList.add('text-muted');
        }
        else {
            deliveryPriceBadge.classList.remove('text-muted');
        }
    }

    /**
     * Remove all children of the provided element from the DOM.
     *
     * @private
     * @param {Element} el - The element to clear.
     * @return {void}
     */
    _clearElement(el) {
        while (el.firstChild) {
            el.removeChild(el.lastChild);
        }
    }

    // #=== ADDRESS FLOW ===#

    /**
     * Select the billing address matching the currently selected delivery address.
     *
     * @private
     * @param selectedPartnerId - The partner id of the selected delivery address.
     * @return {void}
     */
    _selectMatchingBillingAddressCard(selectedPartnerId) {
        const previousAddress = this._getSelectedAddress('billing');
        this._tuneDownAddressCard(previousAddress);
        const billingAddress = this.el.querySelector(
            `.card[data-partner-id="${selectedPartnerId}"][data-address-type="billing"]`
        );
        this._highlightAddressCard(billingAddress);
    }

    /**
     * Set the billing or delivery address on the order.
     *
     * @param addressType - The type of the address to set: 'delivery' or 'billing'.
     * @param partnerId - The partner id of the address to set.
     * @return {void}
     */
    async updateAddress(addressType, partnerId) {
        await rpc('/shop/update_address', {
            address_type: addressType,
            partner_id: partnerId,
            use_delivery_as_billing: this.useDeliveryAsBillingToggle?.checked
        });
    }

    /**
     * Open the address edit dialog, filled with the address of the clicked card.
     *
     * @param {Event} ev
     * @return {void}
     */
    async openEditAddressDialog(ev) {
        ev.preventDefault();
        const card = ev.currentTarget.closest('[name="address_card"]');
        const modalBodyEl = this.editAddressModalEl.querySelector('.modal-body');

        // Stop any interaction (e.g. a previous dialog use) still running on the modal body
        // before replacing its content, then (re)start them on the freshly injected form.
        this.services['public.interactions'].stopInteractions(modalBodyEl);
        const formHtml = await this.waitFor(rpc('/shop/address/dialog', {
            partner_id: card.dataset.partnerId,
            address_type: card.dataset.addressType,
        }));
        // The `.o_customer_address_fill` class is added here, on the wrapper we're about to fill,
        // rather than kept statically on the empty modal body: `CustomerAddress` mounts on any
        // match for that selector and assumes a form is already inside, which would crash on an
        // empty container present in the DOM before the dialog is ever opened.
        modalBodyEl.replaceChildren();
        const formWrapperEl = document.createElement('div');
        formWrapperEl.className = 'o_customer_address_fill';
        formWrapperEl.innerHTML = formHtml;
        modalBodyEl.appendChild(formWrapperEl);
        this.services['public.interactions'].startInteractions(modalBodyEl);

        this.bootstrap.getOrCreateInstance(window.Modal, this.editAddressModalEl).show();
    }

    /**
     * Submit the address form displayed in the edit dialog.
     *
     * Not bound to the generic `website_sale_main_button` handler (`CustomerAddress.saveAddress`)
     * on purpose: that name is also used by the page's own "Checkout" button, and binding both
     * would submit the dialog's form when the customer only meant to move to the next step.
     *
     * @return {void}
     */
    async saveEditAddressDialog() {
        const formEl = this.editAddressModalEl.querySelector('form.address_autoformat');
        if (!formEl || !formEl.reportValidity()) {
            return;
        }

        const result = await this.waitFor(
            this.services['http'].post(formEl.dataset.submitUrl, new FormData(formEl))
        );
        if (result.redirectUrl) {
            redirect(result.redirectUrl);
            return;
        }
        formEl.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
        (result.invalid_fields || []).forEach((fieldName) => {
            formEl[fieldName]?.classList.add('is-invalid');
        });
    }

    // #=== DELIVERY FLOW ===#

    /**
     * Change the delivery method to the one whose radio is selected and fetch all delivery rates.
     *
     * @private
     * @return {void}
     */
    async _prepareDeliveryMethods() {
        // Load the radios from the DOM here to update them if the template is re-rendered.
        this.dmRadios = Array.from(document.querySelectorAll('input[name="o_delivery_radio"]'));
        if (this.dmRadios.length > 0) {
            const checkedRadio = this._getSelectedDeliveryRadio();
            this._disableMainButton();
            if (checkedRadio) {
                await this.waitFor(this._updateDeliveryMethod(checkedRadio));
                this._enableMainButton();
            }
        }
        // Asynchronously fetch delivery rates to mitigate delays from third-party APIs
        await Promise.all(this.dmRadios.filter(radio => !radio.checked).map(async radio => {
            this._showLoadingBadge((radio));
            const rateData = await this.waitFor(this._getDeliveryRate(radio));
            this._updateAmountBadge(radio, rateData);
        }));
    }

    /**
     * Check if the delivery method is selected and available.
     *
     * @private
     * @return {boolean} Whether the delivery method is ready.
     */
    _isDeliveryMethodReady() {
        if (this.dmRadios.length === 0) { // No delivery method is available.
            return true; // Ignore the check.
        }
        const checkedRadio = this._getSelectedDeliveryRadio();
        return checkedRadio && !checkedRadio.disabled;
    }

    /**
     * Get the delivery rate of the delivery method linked to the provided radio.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {Object} The delivery rate data.
     */
    async _getDeliveryRate(radio) {
        return await rpc('/shop/get_delivery_rate', {'dm_id': radio.dataset.dmId});
    }

    /**
     * Set the delivery method on the order and return the result values.
     *
     * @private
     * @param {Integer} dmId - The id of selected delivery method.
     * @return {Object} The result values.
     */
    async _setDeliveryMethod(dmId) {
        return await rpc('/shop/set_delivery_method', {'dm_id': dmId});
    }

    // #=== GETTERS & SETTERS ===#

    /** Determine and return the selected address who card has the class rowAddrClass.
     *
     * @private
     * @param addressType - The type of the address: 'billing' or 'delivery'.
     * @return {Element}
     */
    _getSelectedAddress(addressType) {
        return this.el.querySelector(`.card.bg-400[data-address-type="${addressType}"]`);
    }

    /**
     * Return whether the "use delivery as billing" toggle is checked or a billing address is
     * selected.
     *
     * @private
     * @return {boolean} - Whether a billing address is selected.
     */
    _isBillingAddressSelected() {
        const billingCards = this.el.querySelectorAll('.card[data-address-type="billing"]');
        if (billingCards.length === 0) {
            // No address list to pick from (e.g. the address form is being filled in): ignore
            // the check.
            return true;
        }
        const billingAddressSelected = Boolean(
            this.el.querySelector('.card.bg-400[data-address-type="billing"]')
        );
        return billingAddressSelected || this.useDeliveryAsBillingToggle?.checked;
    }

    /**
     * Create and return an element representing a loading spinner.
     *
     * @private
     * @return {Element} The created element.
     */
    _createLoadingElement() {
        const loadingElement = document.createElement('i');
        loadingElement.classList.add('oi', 'oi-spin', 'center');
        loadingElement.dataset.icon = "autorenew";
        return loadingElement;
    }

    /**
     * Return the delivery price badge element of the delivery method linked to the provided radio.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {Element} The delivery price badge element of the linked delivery method.
     */
    _getDeliveryPriceBadge(radio) {
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        return deliveryMethodContainer.querySelector('.o_wsale_delivery_price_badge');
    }

    /**
     * Return the container element of the delivery method linked to the provided element.
     *
     * @private
     * @param {Element} el - The element linked to the delivery method.
     * @return {Element} The container element of the linked delivery method.
     */
    _getDeliveryMethodContainer(el) {
        return el.closest('[name="o_delivery_method"]');
    }

    /**
     * Returns the selected delivery method radio element.
     *
     * @returns {Element} The selected radio button element.
     */
    _getSelectedDeliveryRadio(){
        return this.el.querySelector('input[name="o_delivery_radio"]:checked');
    }

}

registry
    .category('public.interactions')
    .add('website_sale.checkout', Checkout);
