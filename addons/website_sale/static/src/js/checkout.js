import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { renderToElement } from '@web/core/utils/render';
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.websiteSaleCheckout = publicWidget.Widget.extend({
    selector: '#shop_checkout',
    events: {
        // Addresses
        'click .js_change_billing': '_changeBillingAddress',
        'click .js_change_delivery': '_changeDeliveryAddress',
        'click .js_edit_address': '_preventChangingAddress',
        // Delivery methods
        'click [name="o_delivery_radio"]': '_selectDeliveryMethod',
        'click [name="o_select_pickup_location"]': '_selectPickupLocation',
        'click [name="o_remove_pickup_location"]': '_removePickupLocation',
    },

    // #=== WIDGET LIFECYCLE ===#

    async start() {
        this.mainButton = document.querySelector('a[name="website_sale_main_button"]');
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
        await this._changeAddress(ev, 'all_billing', 'js_change_billing');
    },

    /**
     * Change the delivery address.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _changeDeliveryAddress (ev) {
        await this._changeAddress(ev, 'all_delivery', 'js_change_delivery');
    },

    /**
     * Set the billing or delivery address on the order and update the corresponding card.
     *
     * @private
     * @param {Event} ev
     * @param {String} rowAddrClass - The class of the selected address row: 'all_billing' for a
     *                                billing, 'all_delivery' for a delivery one.
     * @param {String} cardClass - The class of an unselected address card: 'js_change_billing' for
     *                             a billing address, `js_change_delivery` for a delivery one.
     * @return {void}
     */
    async _changeAddress(ev, rowAddrClass, cardClass) {
        const oldCard = document.querySelector(
            `.${rowAddrClass} .card.border.border-primary`
        );
        oldCard.classList.add(cardClass);
        oldCard.classList.remove('bg-primary', 'border', 'border-primary');

        const newCard = ev.currentTarget.closest('div.one_kanban').querySelector('.card');
        newCard.classList.remove(cardClass);
        newCard.classList.add('bg-primary', 'border', 'border-primary');
        const mode = newCard.dataset.mode;
        await rpc(
            '/shop/cart/update_address',
            {
                mode: mode,
                partner_id: newCard.dataset.partnerId,
            }
        )

        // When the delivery address is changed, update the available delivery methods.
        if (mode === 'shipping') {
            document.getElementById('o_delivery_form').innerHTML = await rpc(
                '/shop/delivery_methods'
            );
            await this._prepareDeliveryMethods();
        }
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

        // Display a list of closest pickup locations if required for the selected delivery method.
        await this._showClosestPickupLocations(checkedRadio);
    },

    /**
     * Assign the selected pickup location to the order and display its address.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _selectPickupLocation(ev) {
        ev.stopPropagation();
        const deliverMethodContainer = this._getDeliveryMethodContainer(ev.currentTarget);
        const radio = deliverMethodContainer.querySelector('input[type="radio"]');
        const pickupLocationList = this._getPickupLocationList(deliverMethodContainer);
        const pickupLocation = ev.target.previousElementSibling.innerText;
        await this._setPickupLocation(pickupLocation);
        this._clearElement(pickupLocationList);
        await this._showPickupLocation(radio);
        this._enableMainButton();
    },

    /**
     * Unset the selected pickup location from the order and display the available pickup locations.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _removePickupLocation(ev) {
        ev.stopPropagation();
        this._disableMainButton();
        await this._setPickupLocation(null);
        const radio = this._getDeliveryMethodContainer(ev.currentTarget).querySelector(
            'input[type="radio"]'
        );
        await this._showPickupLocation(radio);
        await this._showClosestPickupLocations(radio);
    },

    // #=== DOM MANIPULATION ===#

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
        if (this._isDeliveryMethodReady()) {
            this.mainButton?.classList.remove('disabled');
        }
    },

    /**
     * Hide the selected pickup location.
     *
     * @private
     * @return {void}
     */
    _hidePickupLocation() {
        const pickupLocations = document.querySelectorAll('.o_pickup_location')
        pickupLocations.forEach(pickupLocation => { // Whichever location was set ¯\_(ツ)_/¯
            pickupLocation.querySelector('[name="o_pickup_location_name"]').innerText = '';
            pickupLocation.querySelector('[name="o_pickup_location_address"]').innerText = '';
            pickupLocation.classList.add('d-none');
        });
    },

    /**
     * Hide the list of available pickup locations.
     *
     * @private
     * @return {void}
     */
    _hidePickupLocationList() {
        const listLocations = document.querySelectorAll('[name="o_list_pickup_locations"]');
        listLocations.forEach(pickupLocationList =>  { // Whichever list was built ¯\_(ツ)_/¯
            this._clearElement(pickupLocationList);
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
                await this._showPickupLocation(checkedRadio);
                this._enableMainButton();
                await this._showClosestPickupLocations(checkedRadio);
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
     * @param {Integer} dm_id - The id of selected delivery method.
     * @return {Object} The result values.
     */
    async _setDeliveryMethod(dm_id) {
        return await rpc('/shop/set_delivery_method', {'dm_id': dm_id});
    },

    /**
     * Fetch and display the closest pickup locations for the selected shipping address.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {void}
     */
    async _showClosestPickupLocations(radio) {
        this._hidePickupLocationList();
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        if (!this._isPickupLocationMissing(radio) || radio.disabled) {
            return;  // DM does not have a pickup location, or fetching the delivery rate failed.
        }
        const pickupLocationList = this._getPickupLocationList(deliveryMethodContainer);
        const title = document.createElement('div');
        title.classList.add('h6', 'm-3');
        title.textContent = _t("Please select a pick-up point");
        title.style.cssText = 'color:red;';
        pickupLocationList.append(title);
        const deliveryType = radio.dataset.deliveryType;
        pickupLocationList.appendChild(this._createLoadingElement());
        const data = await rpc("/shop/get_close_locations");
        // Remove the loading spinner.
        pickupLocationList.removeChild(pickupLocationList.querySelector('i'));
        if (data.error) {
            const errorMessage = document.createElement('em');
            errorMessage.innerText = data.error
            pickupLocationList.appendChild(errorMessage);
            return;
        }
        // The corresponding delivery method template to render the pickup locations.
        const templateToRender = `${deliveryType}_pickup_location_list`;
        const context = {
            partner_address: data.partner_address,
            pickup_locations: data.close_locations,
        };
        pickupLocationList.append(renderToElement(templateToRender, context));
    },

    /**
     * Set the pickup location on the order.
     *
     * @private
     * @param {String} pickupLocationData - The pickup location's data to set.
     * @return {void}
     */
    async _setPickupLocation(pickupLocationData) {
        await rpc("/shop/set_pickup_location", {pickup_location_data: pickupLocationData});
    },

    /**
     * Show the pickup location if selected.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {void}
     */
    async _showPickupLocation(radio) {
        if (!this._isPickupLocationRequired(radio)) {
            return
        }

        const data = await rpc('/shop/get_pickup_location');
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        const orderLoc = deliveryMethodContainer.querySelector('.o_pickup_location');
        const pickupLoc = data['pickup_address'];
        orderLoc.querySelector('[name="o_pickup_location_name"]').innerText = data.name || '';
        orderLoc.querySelector('[name="o_pickup_location_address"]').innerText = pickupLoc || '';
        if (pickupLoc) {
            orderLoc.classList.remove("d-none");
        } else {
            orderLoc.classList.add("d-none");
        }
    },

    // #=== GETTERS & SETTERS ===#

    /**
     * Return whether a pickup location is required but not selected.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the delivery method.
     * @return {boolean} Whether a required pickup location is missing.
     */
    _isPickupLocationMissing(radio) {
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        const address = deliveryMethodContainer.querySelector(
            '[name="o_pickup_location_address"]'
        ).innerText;
        return this._isPickupLocationRequired(radio) && address === '';
    },

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
     * Return the pickup location list element of the provided delivery method container.
     *
     * @private
     * @param {Element} deliveryMethodContainer - The container element of the linked delivery
     *                                            method.
     * @return {Element} The pickup location list element of the linked delivery method.
     */
    _getPickupLocationList(deliveryMethodContainer) {
        return deliveryMethodContainer.querySelector('[name="o_list_pickup_locations"]');
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
