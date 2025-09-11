import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';

export class Checkout extends Interaction {
    static selector = '#shop_checkout';
    dynamicContent = {
        // Addresses
        '.card': { 't-on-click': this.changeAddress },
        // Cancel the address change to allow the redirect to the edit page to take place.
        '.js_edit_address': { 't-on-click.stop': () => {} },
        '#use_delivery_as_billing': { 't-on-change': this.toggleBillingAddressRow },
        // Delivery methods
        '[name="o_delivery_radio"]': { 't-on-click': this.selectDeliveryMethod },
        '[name="o_pickup_location_selector"]': { 't-on-click': this.selectPickupLocation },
    };

    setup() {
        // There are two main buttons in the DOM (one for mobile and one for desktop).
        // We need to get the one that's actually displayed.
        this.mainButton = Array.from(document.getElementsByName('website_sale_main_button'))
            .find(button => button.offsetParent !== null);
        this.useDeliveryAsBillingToggle = document.querySelector('#use_delivery_as_billing');
        this.billingContainer = this.el.querySelector('#billing_container');
        this.addBillingAddressBtn = this.el.querySelector('.o_add_billing_address_btn');
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
        if (addressType === 'delivery' || this.billingContainer.dataset.deliveryAddressDisabled) {
            if (this.billingContainer.dataset.deliveryAddressDisabled) {
                // If a delivery address is disabled in the settings, use a billing address as
                // a delivery one.
                await this.waitFor(this.updateAddress('delivery', selectedPartnerId));
            }
            if (this.useDeliveryAsBillingToggle?.checked) {
                await this.waitFor(this._selectMatchingBillingAddress(selectedPartnerId));
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
        if (addDeliveryAddressButton) {  // If `Add address` button for delivery.
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
            const selectedDeliveryAddress = this._getSelectedAddress('delivery');
            await this.waitFor(
                this._selectMatchingBillingAddress(selectedDeliveryAddress.dataset.partnerId)
            );
        } else {
            this._disableMainButton();
            this.billingContainer.classList.remove('d-none'); // Show the billing address row.
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

        // Hide and reset the order location name and address if defined.
        this._hidePickupLocation();

        // Fetch delivery rates and update the cart summary and the price badge accordingly.
        await this.waitFor(this._updateDeliveryMethod(checkedRadio));

        // Re-enable the main button after delivery rates have been fetched.
        this._enableMainButton();

        // Show a button to open the location selector if required for the selected delivery method.
        await this._showPickupLocation(checkedRadio);
    }

    /**
     * Fetch and display the closest pickup locations based on the zip code.
     *
     * @param {Event} ev
     * @return {void}
     */
    async selectPickupLocation(ev) {
        const { zipCode, locationId } = ev.currentTarget.dataset;
        const deliveryMethodContainer = this._getDeliveryMethodContainer(ev.currentTarget);
        this.services.dialog.add(LocationSelectorDialog, {
            zipCode: zipCode,
            selectedLocationId: locationId,
            isFrontend: true,
            save: async location => {
                const jsonLocation = JSON.stringify(location);
                // Assign the selected pickup location to the order.
                await this.waitFor(this._setPickupLocation(jsonLocation));

                //  Show and set the order location details.
                this._updatePickupLocation(deliveryMethodContainer, location, jsonLocation);

                this._enableMainButton();
            },
        });
    }

    // #=== DOM MANIPULATION ===#

    /**
     * Update the pickup location address elements and the 'edit' button's values.
     *
     * @private
     * @param deliveryMethodContainer - The container element of the delivery method.
     * @param location - The selected location as an object.
     * @param jsonLocation - The selected location as an JSON string.
     * @return {void}
     */
    _updatePickupLocation(deliveryMethodContainer, location, jsonLocation) {
        const pickupLocation = deliveryMethodContainer.querySelector('[name="o_pickup_location"]');
        pickupLocation.querySelector('[name="o_pickup_location_name"]').innerText = location.name;
        pickupLocation.querySelector(
            '[name="o_pickup_location_address"]'
        ).innerText = `${location.street} ${location.zip_code} ${location.city}`;
        const editPickupLocationButton = pickupLocation.querySelector(
            'span[name="o_pickup_location_selector"]'
        );
        editPickupLocationButton.dataset.locationId = location.id;
        editPickupLocationButton.dataset.zipCode = location.zip_code;
        editPickupLocationButton.dataset.pickupLocationData = jsonLocation;
        pickupLocation.querySelector(
            '[name="o_pickup_location_details"]'
        ).classList.remove('d-none');

        // Remove the button.
        pickupLocation.querySelector('button[name="o_pickup_location_selector"]')?.remove();
    }

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
     * Hide the pickup location.
     *
     * @private
     * @return {void}
     */
    _hidePickupLocation() {
        const pickupLocations = document.querySelectorAll(
            '[name="o_pickup_location"]:not(.d-none)'
        );
        pickupLocations.forEach(pickupLocation =>
            pickupLocation.classList.add('d-none') // Hide the whole div.
        );
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
        const amountTax = targetEl.querySelector('tr[name="o_order_total_taxes"] .monetary_field');
        const amountTotal = targetEl.parentElement.querySelectorAll(
            'tr[name="o_order_total"] .monetary_field, #amount_total_summary.monetary_field'
        );

        // When no dm is set and a price span is hidden, hide the message and show the price span.
        if (amountDelivery.classList.contains('d-none')) {
            amountDelivery.querySelector('span[name="o_message_no_dm_set"]').classList.add('d-none');
            amountDelivery.classList.remove('d-none');
        }

        amountDelivery.innerHTML = result.amount_delivery;
        amountUntaxed.innerHTML = result.amount_untaxed;
        amountTax.innerHTML = result.amount_tax;
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
    async _selectMatchingBillingAddress(selectedPartnerId) {
        const previousAddress = this._getSelectedAddress('billing');
        this._tuneDownAddressCard(previousAddress);
        await this.waitFor(this.updateAddress('billing', selectedPartnerId));
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
        await rpc('/shop/update_address', {address_type: addressType, partner_id: partnerId});
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
            const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
            this._disableMainButton();
            if (checkedRadio) {
                await this.waitFor(this._updateDeliveryMethod(checkedRadio));
                this._enableMainButton();
                await this._showPickupLocation(checkedRadio);
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
     * Check if the delivery method is selected and if the pickup point is selected if needed.
     *
     * @private
     * @return {boolean} Whether the delivery method is ready.
     */
    _isDeliveryMethodReady() {
        if (this.dmRadios.length === 0) { // No delivery method is available.
            return true; // Ignore the check.
        }
        const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
        return checkedRadio
            && !checkedRadio.disabled
            && !this._isPickupLocationMissing(checkedRadio);
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

    /**
     * Show the pickup location information or the button to open the location selector.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {void}
     */
    async _showPickupLocation(radio) {
        if (!radio.dataset.isPickupLocationRequired || radio.disabled) {
            return;  // Fetching the delivery rate failed.
        }
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        const pickupLocation = deliveryMethodContainer.querySelector('[name="o_pickup_location"]');

        const editPickupLocationButton = pickupLocation.querySelector(
            'span[name="o_pickup_location_selector"]'
        );
        if (editPickupLocationButton.dataset.pickupLocationData) {
            await this.waitFor(
                this._setPickupLocation(editPickupLocationButton.dataset.pickupLocationData)
            );
        }

        pickupLocation.classList.remove('d-none'); // Show the whole div.
    }

    /**
     * Set the pickup location on the order.
     *
     * @private
     * @param {String} pickupLocationData - The pickup location's data to set.
     * @return {void}
     */
    async _setPickupLocation(pickupLocationData) {
        await rpc('/website_sale/set_pickup_location', {pickup_location_data: pickupLocationData});
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
        loadingElement.classList.add('fa', 'fa-circle-o-notch', 'fa-spin', 'center');
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
     * Return whether a pickup location is required but not selected.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {boolean} Whether a required pickup location is missing.
     */
    _isPickupLocationMissing(radio) {
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        if (!this._isPickupLocationRequired(radio)) return false;
        return !deliveryMethodContainer.querySelector(
            'span[name="o_pickup_location_selector"]'
        ).dataset.locationId;
    }

    /**
     * Return whether a pickup is required for the delivery method linked to the provided radio.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {bool} Whether a pickup is needed.
     */
    _isPickupLocationRequired(radio) {
        return Boolean(radio.dataset.isPickupLocationRequired);
    }
}

registry
    .category('public.interactions')
    .add('website_sale.checkout', Checkout);
