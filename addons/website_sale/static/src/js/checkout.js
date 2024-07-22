import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.websiteSaleCheckout = publicWidget.Widget.extend({
    selector: '#shop_checkout',
    events: {
        // Addresses
        'click .js_change_billing': '_changeBillingAddress',
        'click .js_change_delivery': '_changeDeliveryAddress',
        'click .js_edit_address': '_preventChangingAddress',
        'change #use_same_as_delivery': '_toggleBillingAddresses',
        // Delivery methods
        'click [name="o_delivery_radio"]': '_selectDeliveryMethod',
        'click [name="o_pickup_location_selector"]': '_selectPickupLocation',
    },

    // #=== WIDGET LIFECYCLE ===#

    async start() {
        this.mainButton = document.querySelector('a[name="website_sale_main_button"]');
        this.billingRowClass = 'all_billing';
        this.deliveryRowClass = 'all_delivery';
        this.deliveryJSClass = 'js_change_delivery';
        this.billingJSClass = 'js_change_billing';
        this.use_same_as_delivery = document.querySelector('#use_same_as_delivery');
        await this._prepareDeliveryMethods();
    },

    // #=== EVENT HANDLERS ===#

    /**
     * Change the billing address.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _changeBillingAddress (ev) {
        await this._changeAddress(ev, this.billingRowClass);
    },

    /**
     * Show billing addresses row when the user checks the 'use same as delivery' else hide it.
     *
     * @param ev
     * @return {void}
     * @private
     */
    async _toggleBillingAddresses(ev) {
        const billingContainer = document.querySelector('#billing_container');
        const oldCard = this.findSelectedCardAddress(this.billingRowClass);
        // Reset selected billing card address if any.
        this.removePrimaryClassFromAddressCard(oldCard, this.billingRowClass);
        if (ev.target.checked) {
            billingContainer.classList.add('d-none');  // Hide billing addresses.
            const selectedDeliveryCard = this.findSelectedCardAddress(this.deliveryRowClass);
            // Set billing address same as the selected delivery address.
            await this.updateAddress('billing', selectedDeliveryCard.dataset.partnerId);
            this._enableMainButton();  // Try to enable the button.
        } else {
            this._disableMainButton();
            billingContainer.classList.remove('d-none');  // Show billing addresses.
        }
    },

    /**
     * Change the delivery address.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _changeDeliveryAddress (ev) {
        await this._changeAddress(ev, this.deliveryRowClass);
    },

    /**
     * Set the billing or delivery address on the order and update the corresponding card.
     *
     * @private
     * @param {Event} ev
     * @param {String} rowAddrClass - The class of the selected address row: 'all_billing' for a
     *                                billing, 'all_delivery' for a delivery one.
     * @return {void}
     */
    async _changeAddress(ev, rowAddrClass) {
        const oldCard = this.findSelectedCardAddress(rowAddrClass);
        this.removePrimaryClassFromAddressCard(oldCard, rowAddrClass);

        const newCard = ev.currentTarget.closest('div.one_kanban').querySelector('.card');
        this.addPrimaryClassToAddressCard(newCard, rowAddrClass);
        const addressType = newCard.dataset.addressType;
        await this.updateAddress(addressType, newCard.dataset.partnerId);
        this._enableMainButton();  // Try to enable the button.
        // When the delivery address is changed, update the available delivery methods.
        if (addressType === 'delivery') {
            if (this.use_same_as_delivery.checked) {
                // Set billing address same as the selected delivery address.
                await this.updateAddress('billing', newCard.dataset.partnerId);
            }
            document.getElementById('o_delivery_form').innerHTML = await rpc(
                '/shop/delivery_methods'
            );
            await this._prepareDeliveryMethods();
        }
    },

    /**
     * Set billing or delivery address on the order.
     *
     * @param addressType
     * @param partnerId
     * @return {Promise<void>}
     */
    async updateAddress(addressType, partnerId) {
        await rpc(
            '/shop/update_address',
            {
                address_type: addressType,
                partner_id: partnerId,
            }
        )
    },

    /**
     * Cancel the address change to allow the redirect to the edit page to take place.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    _preventChangingAddress(ev) {
        ev.stopPropagation();
    },

    /**
     * Fetch the delivery rate for the selected delivery method and update the displayed amounts.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _selectDeliveryMethod(ev) {
        const checkedRadio = ev.currentTarget;
        if (checkedRadio.disabled) {  // The delivery rate request failed.
            return; // Failing delivery methods cannot be selected.
        }

        // Disable the main button while fetching delivery rates.
        this._disableMainButton();

        // Hide and reset the order location name and address if defined.
        this._hidePickupLocation();

        // Fetch delivery rates and update the cart summary and the price badge accordingly.
        await this._updateDeliveryMethod(checkedRadio);

        // Re-enable the main button after delivery rates have been fetched.
        this._enableMainButton();

        // Show a button to open the location selector if required for the selected delivery method.
        await this._showPickupLocation(checkedRadio);
    },

    /**
     * Fetch and display the closest pickup locations based on the zip code.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _selectPickupLocation(ev) {
        const { zipCode, locationId } = ev.currentTarget.dataset;
        this.call('dialog', 'add', LocationSelectorDialog, {
            zipCode: zipCode,
            selectedLocationId: locationId,
            isFrontend: true,
            save: async location => {
                const jsonLocation = JSON.stringify(location);
                // Assign the selected pickup location to the order.
                await this._setPickupLocation(jsonLocation);

                //  Show and set the order location details.
                const deliveryMethodContainer = this._getDeliveryMethodContainer(ev.currentTarget);
                const pickupLocation = deliveryMethodContainer.querySelector(
                    '[name="o_pickup_location"]'
                );
                pickupLocation.querySelector(
                    '[name="o_pickup_location_name"]'
                ).innerText = location.name;
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
                pickupLocation.querySelector(
                    'button[name="o_pickup_location_selector"]'
                )?.remove();

                this._enableMainButton();
            },
        });
    },

    // #=== DOM MANIPULATION ===#
    /**
     * Reset the selected card.
     *
     * @param card
     * @param rowAddrClass
     */
    removePrimaryClassFromAddressCard(card, rowAddrClass) {
        const cardClass = (rowAddrClass === this.deliveryRowClass) ? this.deliveryJSClass : this.billingJSClass;
        card?.classList.add(cardClass);
        card?.classList.remove('bg-primary', 'border', 'border-primary');
    },

    /**
     * Select the card.
     *
     * @param card
     * @param rowAddrClass
     */
    addPrimaryClassToAddressCard(card, rowAddrClass) {
        const cardClass = (rowAddrClass === this.deliveryRowClass) ? this.deliveryJSClass : this.billingJSClass;
        card?.classList.remove(cardClass);
        card?.classList.add('bg-primary', 'border', 'border-primary');
    },

    /**
     * Find the selected card of rowAddrClass.
     *
     * @param rowAddrClass
     * @return {Element}
     */
    findSelectedCardAddress(rowAddrClass) {
        return document.querySelector(`.${rowAddrClass} .card.border.border-primary`);
    },

    /**
     * Disable the main button.
     *
     * @private
     * @return {void}
     */
    _disableMainButton() {
        this.mainButton?.classList.add('disabled');
    },

    /**
     * Enable the main button if a delivery method is selected.
     *
     * @private
     * @return {void}
     */
    _enableMainButton() {
        if (this._isDeliveryMethodReady() && this._isBillingAddressSelected()) {
            this.mainButton?.classList.remove('disabled');
        }
    },

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
        pickupLocations.forEach(pickupLocation => {
            pickupLocation.classList.add('d-none'); // Hide the whole div.
        });
    },

    /**
     * Set the delivery method on the order and update the price badge and cart summary.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {void}
     */
    async _updateDeliveryMethod(radio) {
        this._showLoadingBadge(radio);
        const result = await this._setDeliveryMethod(radio.dataset.dmId);
        this._updateAmountBadge(radio, result);
        this._updateCartSummary(result);
    },

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
    },

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
             // If it's a free delivery (`free_over` field), show 'Free', not '$ 0'.
             if (rateData.is_free_delivery) {
                 deliveryPriceBadge.textContent = _t("Free");
             } else {
                 deliveryPriceBadge.innerHTML = rateData.amount_delivery;
             }
             this._toggleDeliveryMethodRadio(radio);
        } else {
            deliveryPriceBadge.textContent = rateData.error_message;
            this._toggleDeliveryMethodRadio(radio, true);
        }
    },

    /**
     * Update the order summary table with the delivery rate of the selected delivery method.
     *
     * @private
     * @param {Object} result - The order summary values.
     * @return {void}
     */
    _updateCartSummary(result) {
        const amountDelivery = document.querySelector('#order_delivery .monetary_field');
        const amountUntaxed = document.querySelector('#order_total_untaxed .monetary_field');
        const amountTax = document.querySelector('#order_total_taxes .monetary_field');
        const amountTotal = document.querySelectorAll(
            '#order_total .monetary_field, #amount_total_summary.monetary_field'
        );
        amountDelivery.innerHTML = result.amount_delivery;
        amountUntaxed.innerHTML = result.amount_untaxed;
        amountTax.innerHTML = result.amount_tax;
        amountTotal.forEach(total => total.innerHTML = result.amount_total);
    },

    /**
     * Enable or disable radio selection for a delivery method.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @param {Boolean} disable - Whether the radio should be disabled.
     */
    _toggleDeliveryMethodRadio(radio, disable=false) {
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        radio.disabled = disable;
        if (disable) {
            deliveryMethodContainer.classList.add('text-muted');
        }
        else {
            deliveryMethodContainer.classList.remove('text-muted');
        }
    },

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
    },

    /**
     * Checks if `use same as delivery` is checked, otherwise if a billing address card is selected.
     *
     * @return {boolean} - Whether a billing address is selected.
     * @private
     */

    _isBillingAddressSelected() {
        return (
            this.findSelectedCardAddress(this.billingRowClass) || this.use_same_as_delivery.checked
        );
    },

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
                await this._updateDeliveryMethod(checkedRadio);
                this._enableMainButton();
            }
        }
        // Asynchronously fetch delivery rates to mitigate delays from third-party APIs
        await Promise.all(this.dmRadios.filter(radio => !radio.checked).map(async radio => {
            this._showLoadingBadge((radio));
            const rateData = await this._getDeliveryRate(radio);
            this._updateAmountBadge(radio, rateData);
        }));
    },

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
    },

    /**
     * Get the delivery rate of the delivery method linked to the provided radio.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {Object} The delivery rate data.
     */
    async _getDeliveryRate(radio) {
        return await rpc('/shop/get_delivery_rate', {'dm_id': radio.dataset.dmId});
    },

    /**
     * Set the delivery method on the order and return the result values.
     *
     * @private
     * @param {Integer} dmId - The id of selected delivery method.
     * @return {Object} The result values.
     */
    async _setDeliveryMethod(dmId) {
        return await rpc('/shop/set_delivery_method', {'dm_id': dmId});
    },

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
            await this._setPickupLocation(editPickupLocationButton.dataset.pickupLocationData);
        }

        pickupLocation.classList.remove('d-none'); // Show the whole div.
    },

    /**
     * Set the pickup location on the order.
     *
     * @private
     * @param {String} pickupLocationData - The pickup location's data to set.
     * @return {void}
     */
    async _setPickupLocation(pickupLocationData) {
        await rpc('/website_sale/set_pickup_location', {pickup_location_data: pickupLocationData});
    },

    // #=== GETTERS & SETTERS ===#

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
    },

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
    },

    /**
     * Return the container element of the delivery method linked to the provided element.
     *
     * @private
     * @param {Element} el - The element linked to the delivery method.
     * @return {Element} The container element of the linked delivery method.
     */
    _getDeliveryMethodContainer(el) {
        return el.closest('[name="o_delivery_method"]');
    },

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
    },

    /**
     * Return whether a pickup is required for the delivery method linked to the provided radio.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {bool} Whether a pickup is needed.
     */
    _isPickupLocationRequired(radio) {
        return Boolean(radio.dataset.isPickupLocationRequired);
    },

});

export default publicWidget.registry.websiteSaleCheckout;
