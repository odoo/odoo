import { useLayoutEffect, useState } from '@web/owl2/utils';
import { Component, onMounted, onWillUnmount } from '@odoo/owl';
import { browser } from '@web/core/browser/browser';
import { Dialog } from '@web/core/dialog/dialog';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { useDebounced } from '@web/core/utils/timing';
import { LocationList } from '@website_sale_stock/js/location_selector/location_list/location_list';
import { MapContainer } from '@website_sale_stock/js/location_selector/map_container/map_container';

export class LocationSelectorDialog extends Component {
    static components = { Dialog, LocationList, MapContainer };
    static template = 'website_sale_stock.locationSelector.dialog';
    static props = {
        isFrontend: { type: Boolean, optional: true },
        deliveryMethodId: { type: Number, optional: true },
        countryId: { type: Number, optional: true },
        zipCode: String,
        selectedLocationId: { type: String, optional: true },
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

        this.getLocationUrl = '/website_sale_stock/get_pickup_locations';

        this.debouncedOnResize = useDebounced(this.updateSize, 300);
        this.debouncedSearchButton = useDebounced(() => {
            this.state.locations = [];
            this._loadLocations();
        }, 300);

        onMounted(() => {
            browser.addEventListener('resize', this.debouncedOnResize);
            this.updateSize();
        });
        onWillUnmount(() => browser.removeEventListener('resize', this.debouncedOnResize));

        // Fetch new locations when the zip code is updated.
        useLayoutEffect(
            () => {
                this._loadLocations()
                return () => {
                    this.state.locations = []
                };
            },
            () => [this.state.zipCode]
        );
    }

    get locations() { return this.state.locations; }

    /**
     * Fetch the information needed to get the closest pickup locations
     *
     * @private
     * @return {Object} The result values.
     */
    _getLocationsParams() {
        return {
            zip_code: this.state.zipCode,
            delivery_method_id: this.props.deliveryMethodId,
            country_id: this.props.countryId,
         };
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
     * @return {void}
     */
    async _loadLocations() {
        this.state.error = false;
        const { pickup_locations, error } = await rpc(
            this.getLocationUrl, this._getLocationsParams()
        );
        if (error) {
            this.state.error = error;
            console.error(error);
        } else {
            this._updateLocations(pickup_locations);
            this._selectLocation();
        }
    }

    _updateLocations(locations) {
        this.state.locations = locations;
    }

    _selectLocation() {
        if (!this.locations.find(l => String(l.id) === this.state.selectedLocationId)) {
            this.state.selectedLocationId = this.locations[0]
                ? String(this.locations[0].id)
                : false;
        }
    }

    /**
     * Find the selected location based on its id.
     *
     * @return {Object} The selected location.
     */
    get selectedLocation() {
        return this.state.locations.find(l => String(l.id) === this.state.selectedLocationId);
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
        if (this.state.locations.length === 1) {
            return _t("Pickup Location")
        }
        return _t("Choose a pick-up point");
    }

    /**
     *
     * @return {void}
     */
    updateSize() {
        this.state.isSmall = this.env.isSmall;
    }
}
