import { LocationList } from "@location_selector/location_list/location_list";
import { MapContainer } from "@location_selector/map_container/map_container";
import { Component, onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useDebounced } from "@web/core/utils/timing";

export class LocationSelectorComponent extends Component {
    static components = { LocationList, MapContainer };
    static template = "location_selector.location_selector_component";
    static props = {
        rootEl: Object,
        type: String,
        zoom: String,
        searchbar: Boolean,
        sidebar: Boolean,
        sidebarLocation: String,
        description: Boolean,
        details: String,
        offscreenLocationsHidden: Boolean,
    };

    setup() {
        this.state = useState({
            locations: [],
            error: false,
            viewMode: "list",
            zipCode: "",
            // Some APIs like FedEx use strings to identify locations.
            selectedLocationId: "",
            hiddenLocations: [],
            isSmall: this.env.isSmall,
        });

        this.debouncedOnResize = useDebounced(this.updateSize, 300);
        this.debouncedSearchButton = useDebounced((zipCode) => {
            this.state.locations = [];
            this._updateLocations(zipCode);
        }, 300);

        onMounted(() => {
            browser.addEventListener("resize", this.debouncedOnResize);
            this.updateSize();
        });
        onWillUnmount(() => browser.removeEventListener("resize", this.debouncedOnResize));

        // Fetch new locations when the zip code is updated.
        useEffect(
            (zipCode) => {
                this._updateLocations(zipCode);
                return () => {
                    this.state.locations = [];
                };
            },
            () => [this.state.zipCode]
        );
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    /**
     * Fetch the closest pickup locations based on the input filter.
     *
     * @private
     * @param {String} filter - The filter used to look for locations, will be matched with store name, streen name, city name, zip.
     * @return {Object} The result values.
     */
    getLocations(zipCode) {
        this.state.locations = [];
        const rawLocations = this.props.rootEl.attributes["data-render-list-items"]?.nodeValue;
        if (rawLocations && rawLocations != "undefined") {
            this.state.locations = JSON.parse(rawLocations).filter(({ zip }) =>
                zip?.match(zipCode)
            );
        }
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
    _updateLocations(zipCode) {
        this.getLocations(zipCode);
        if (!this.state.locations.find((l) => String(l.id) === this.state.selectedLocationId)) {
            this.state.selectedLocationId = this.state.locations[0]
                ? String(this.state.locations[0].id)
                : false;
        }
    }

    /**
     * Find the selected location based on its id.
     *
     * @return {Object} The selected location.
     */
    get selectedLocation() {
        return this.state.locations.find((l) => String(l.id) === this.state.selectedLocationId);
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
     * Set the visibleLocationsIds in the state.
     *
     * @param {Array} locationsIds
     * @return {void}
     */
    setHiddenLocations(locationsIds) {
        this.state.hiddenLocations = this.props.offscreenLocationsHidden ? locationsIds : [];
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
        if (this.state.viewMode === "map") {
            return MapContainer;
        }
        return LocationList;
    }

    get validationButtonLabel() {
        return _t("Learn more");
    }

    get postalCodePlaceholder() {
        return _t("Your postal code");
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
