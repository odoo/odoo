import { LocationList } from "@website/components/location_selector/location_list/location_list";
import { MapContainer } from "@website/components/location_selector/map_container/map_container";
import { Component, onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useDebounced } from "@web/core/utils/timing";

export class LocationSelectorComponent extends Component {
    static components = { LocationList, MapContainer };
    static template = "website.locationSelector.component";
    static props = {
        mapZoom: String,
        showSearchbar: Boolean,
        showSidebar: Boolean,
        sidebarLocation: String,
        showDetailsTooltip: Boolean,
        showDetailsTextArea: Boolean,
        hideOffscreenLocations: Boolean,
        locationsList: String,
        showEmail: Boolean,
        showImage: Boolean,
        showPhone: Boolean,
        showWebsite: Boolean,
    };

    setup() {
        this.state = useState({
            locations: [],
            error: false,
            viewMode: "list",
            zipCode: this.props.zipCode,
            selectedLocationId: "",
            isSmall: this.env.isSmall,
        });

        this.debouncedOnResize = useDebounced(this.updateSize, 300);
        this.debouncedSearchButton = useDebounced((zipCode) => {
            this.state.locations = [];
            this._updateLocations(zipCode);
        }, 300);

        onMounted(() => {
            window.addEventListener("resize", this.debouncedOnResize);
            this.updateSize();
        });
        onWillUnmount(() => window.removeEventListener("resize", this.debouncedOnResize));

        // Fetch new locations when the zip code is updated.
        useEffect(
            (zipCode) => {
                this._updateLocations(zipCode);
            },
            () => [this.state.zipCode]
        );
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Update displayed locations based on the zip in the searchbar. Then, if
     * the old selected location is not anymore displayed, select the first
     * location in the list.
     *
     * @private
     * @param {String} searchedZip - The zip code used to look for close locations.
     * @return {void}
     */
    async _updateLocations(searchedZip) {
        const allLocations = JSON.parse(this.props.locationsList || "[]");
        this.state.locations = allLocations
            .filter(({ zip }) => zip?.match(searchedZip))
            .map(({ partner_latitude, partner_longitude, zip, ...rest }) => ({
                ...rest,
                zip_code: zip,
                latitude: partner_latitude,
                longitude: partner_longitude,
            }));
        if (!this.state.locations.find((l) => String(l.id) === this.state.selectedLocationId)) {
            this.state.selectedLocationId = this.state.locations[0]
                ? String(this.state.locations[0].id)
                : false;
        }
    }

    get showListView() {
        return this.props.showSidebar;
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
     * Set the visibleLocations in the state.
     *
     * @param {Array} locationsIds
     * @return {void}
     */
    setVisibleLocations(locationsIds) {
        if (this.props.hideOffscreenLocations) {
            this.state.visibleLocations = new Set(locationsIds);
        }
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
        if (!this.props.showSidebar || this.state.viewMode === "map") {
            return MapContainer;
        }
        return LocationList;
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
