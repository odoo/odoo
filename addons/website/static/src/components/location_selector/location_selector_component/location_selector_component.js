import { LocationList } from "@website/components/location_selector/location_list/location_list";
import { MapContainer } from "@website/components/location_selector/map_container/map_container";
import { Component, onMounted, onWillUnmount, useEffect, props, proxy, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useDebounced } from "@web/core/utils/timing";

export class LocationSelectorComponent extends Component {
    static components = { LocationList, MapContainer };
    static template = "website.locationSelector.component";
    props = props({
        mapZoom: t.string(),
        showSidebar: t.boolean().optional(false),
        showSearchbar: t.boolean().optional(false),
        mapSearchbarPlaceholder: t.string().optional(_t("Your postal code")),
        sidebarLocation: t.string(),
        showDetailsTooltip: t.boolean(),
        showDetailsTextArea: t.boolean(),
        hideOffscreenLocations: t.boolean().optional(false),
        locationsList: t.string(),
        showEmail: t.boolean().optional(false),
        showImage: t.boolean().optional(false),
        showPhone: t.boolean().optional(false),
        showWebsite: t.boolean().optional(false),
        zipCode: t.string().optional(),
        containerEl: t.instanceOf(HTMLElement).optional(),
    });

    setup() {
        this.state = proxy({
            locations: [],
            viewMode: "list",
            zipCode: this.props.zipCode,
            selectedLocationId: "",
            isSmall: this.env.isSmall,
        });

        this.debouncedOnResize = useDebounced(() => this.updateSize(), 300);
        this.debouncedSearchButton = useDebounced(() => {
            this.state.locations = [];
            this._updateLocations(this.state.zipCode);
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

    // This get can be overridden to filter the available locations
    // e.g.: website_sale_collects uses a filter based on country code
    get locations() {
        return this.state.locations;
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

    /**
     *
     * @return {void}
     */
    updateSize() {
        this.state.isSmall = this.env.isSmall;
    }
}
