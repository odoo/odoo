/** @odoo-module **/

import { LocationList } from '@delivery/js/location_selector/location_list/location_list';
import { MapContainer } from '@delivery/js/location_selector/map_container/map_container';
import { Component, onMounted, onWillUnmount, useEffect, useState } from '@odoo/owl';
import { browser } from '@web/core/browser/browser';
import { Dialog } from '@web/core/dialog/dialog';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { useDebounced } from '@web/core/utils/timing';

export class LocationSelectorDialog extends Component {
    static components = { Dialog, LocationList, MapContainer };
    static template = 'delivery.locationSelector.dialog';
    static props = {
        orderId: Number,
        zipCode: String,
        selectedLocationId: { type: String, optional: true},
        save: Function,
        close: Function, // This is the close from the env of the Dialog Component
    };
    static defaultProps = {
        selectedLocationId: false,
    };

    setup() {
        this.state = useState({
            locations: [],
            error: false,
            viewMode: 'list',
            zipCode: this.props.zipCode,
            // Some APIs like FedEx use strings to identify locations.
            selectedLocationId: String(this.props.selectedLocationId),
            isSmall: this.env.isSmall,
        });

        this.getLocationUrl = '/delivery/get_pickup_locations';

        this.debouncedOnResize = useDebounced(this.updateSize, 300);
        this.debouncedSearchButton = useDebounced((zipCode) => {
            this.state.locations = [];
            this._updateLocations(zipCode);
        }, 300);

        onMounted(() => {
            browser.addEventListener('resize', this.debouncedOnResize);
            this.updateSize();
        });
        onWillUnmount(() => browser.removeEventListener('resize', this.debouncedOnResize));

        // Fetch new locations when the zip code is updated.
        useEffect(
            (zipCode) => {
                this._updateLocations(zipCode)
                return () => {
                    this.state.locations = []
                };
            },
            () => [this.state.zipCode]
        );
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    /**
     * Fetch the closest pickup locations based on the zip code.
     *
     * @private
     * @param {String} zip - The zip code used to look for close locations.
     * @return {Object} The result values.
     */
    async _getLocations(zip) {
        return rpc(this.getLocationUrl, {order_id: this.props.orderId, zip_code: zip});
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Get the locations based on the zip code.
     *
     * Select the first location available if no location is currently selected or if the currently
     * selected location is not on the list anymore.
     *
     * @private
     * @param {String} zip - The zip code used to look for close locations.
     * @return {void}
     */
    async _updateLocations(zip) {
        this.state.error = false;
        const { pickup_locations, error } = await this._getLocations(zip);
        if (error) {
            this.state.error = error;
            console.error(error);
        } else {
            this.state.locations = pickup_locations;
            if (!this.state.locations.find(l => String(l.id) === this.state.selectedLocationId)) {
                this.state.selectedLocationId = this.state.locations[0]
                                                ? String(this.state.locations[0].id)
                                                : false;
            }
        }
    }

    /**
     * Set the selectedLocationId in the state.
     *
     * @param {String} locationId
     * @return {void}
     */
    setSelectedLocation(locationId) {
        this.state.selectedLocationId = String(locationId);
    }

    /**
     * Confirm the current selected location.
     *
     * @return {void}
     */
    async validateSelection() {
        if (!this.state.selectedLocationId) return;
        const selectedLocation = this.state.locations.find(
            l => String(l.id) === this.state.selectedLocationId
        );
        await this.props.save(selectedLocation);
        this.props.close();
    }

    //--------------------------------------------------------------------------
    // User Interface
    //--------------------------------------------------------------------------

    /**
     * Determines the component to show in mobile view based on the current state.
     *
     * Returns the MapContainer component if `viewMode` is strictly equal to `map`, else return the
     * List component.
     *
     * @return {Component} The component to show in mobile view.
     */
    get mobileComponent() {
        if (this.state.viewMode === 'map') return MapContainer;
        return LocationList;
    }

    get title() {
        return _t("Choose a pick-up point");
    }

    get validationButtonLabel() {
        return _t("Choose this location");
    }

    get listViewButtonLabel() {
        return _t("List view");
    }

    get mapViewButtonLabel() {
        return _t("Map view");
    }

    get errorMessage() {
        return _t("No result");
    }

    get loadingMessage() {
        return _t("Loading...");
    }

    /**
     *
     * @return {void}
     */
    updateSize() {
        this.state.isSmall = this.env.isSmall;
    }
}
