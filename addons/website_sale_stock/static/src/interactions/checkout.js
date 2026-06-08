import { rpc } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from "@web/public/utils";
import { Checkout } from '@website_sale/interactions/checkout';
import {
    LocationSelectorDialog
} from '@website_sale_stock/js/location_selector/location_selector_dialog/location_selector_dialog';

patch(Checkout.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            "[name='o_pickup_location_selector']": {
                "t-on-click": this.selectPickupLocation.bind(this)
            },
        });
    },

    async selectDeliveryMethod(ev) {
        const checkedRadio = ev.currentTarget;
        if (checkedRadio.disabled) {  // The delivery rate request failed.
            return; // Failing delivery methods cannot be selected.
        }
        // Hide and reset the order location name and address if defined.
        this._hidePickupLocation();
        await this.waitFor(super.selectDeliveryMethod(...arguments));
        // Show a button to open the location selector if required for the selected delivery method.
        this._showPickupLocation(checkedRadio);
    },

    /**
     * Fetch and display the closest pickup locations based on the zip code.
     *
     * @param {Event} ev
     * @return {void}
     */
    async selectPickupLocation(ev) {
        const deliveryMethodContainer = this._getDeliveryMethodContainer(ev.currentTarget);
        this.services.dialog.add(LocationSelectorDialog, {
            ...this._prepareLocationDialogData(ev.currentTarget.dataset),
            save: async locationData => {
                const jsonLocation = JSON.stringify(locationData);
                // Assign the selected pickup location to the order.
                const updatedCartData = await this.waitFor(this._setPickupLocation(jsonLocation));
                this._updateCartSummaries(updatedCartData);

                //  Show and set the order location details.
                this._updatePickupLocation(deliveryMethodContainer, locationData, jsonLocation);

                this._enableMainButton();
            },
        });
    },

    /**
     * Get the data needed by the location dialog.
     *
     * @param {*} dataset
     * @returns {Object}
     */
    _prepareLocationDialogData(dataset) {
        const { zipCode, locationId } = dataset;
        return {
            zipCode: zipCode,
            selectedLocationId: locationId,
            isFrontend: true,
        };
    },

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
        editPickupLocationButton.dataset.countryCode = location.country_code;
        editPickupLocationButton.dataset.locationId = location.id;
        editPickupLocationButton.dataset.zipCode = location.zip_code;
        editPickupLocationButton.dataset.pickupLocationData = jsonLocation;
        pickupLocation.querySelector(
            '[name="o_pickup_location_details"]'
        ).classList.remove('d-none');

        // Remove the button.
        pickupLocation.querySelector('button[name="o_pickup_location_selector"]')?.remove();
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
        pickupLocations.forEach(pickupLocation =>
            pickupLocation.classList.add('d-none') // Hide the whole div.
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
        await this.waitFor(super._prepareDeliveryMethods(...arguments));
        const checkedRadio = this._getSelectedDeliveryRadio();
        if (checkedRadio) {
            this._showPickupLocation(checkedRadio);
        }
    },

    /**
     * Check if the pickup point is selected if needed.
     *
     * @private
     * @return {boolean} Whether the delivery method is ready.
     */
    _isDeliveryMethodReady() {
        let res = super._isDeliveryMethodReady(...arguments);
        const checkedRadio = this._getSelectedDeliveryRadio();
        if (checkedRadio) {
            res &&= !this._isPickupLocationMissing(checkedRadio);
        }
        return res;
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
            const updatedCart = await this.waitFor(
                this._setPickupLocation(editPickupLocationButton.dataset.pickupLocationData)
            );
            this._updateCartSummaries(updatedCart);
        }

        pickupLocation.classList.remove('d-none'); // Show the whole div.
    },

    /**
     * Set the pickup location on the order.
     *
     * @private
     * @param {String} pickupLocationData - The pickup location's data to set.
     * @return {Dict} - Updated cart summary.
     */
    async _setPickupLocation(pickupLocationData) {
        return await rpc('/website_sale_stock/set_pickup_location',
            { pickup_location_data: pickupLocationData }
        );
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
    }
});
