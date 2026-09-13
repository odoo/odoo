import { LocationList } from "@website/components/location_selector/location_list/location_list";
import { MapContainer } from "@website/components/location_selector/map_container/map_container";
import { Component, onMounted, proxy, t, useEffect, useListener, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class LocationSelectorComponent extends Component {
    static components = { LocationList, MapContainer };
    static template = "website.locationSelector.component";
    props = useProps({
        mapZoom: t.string(),
        showSidebar: t.boolean().optional(false),
        showSearchbar: t.boolean().optional(false),
        mapSearchbarPlaceholder: t.string().optional(_t("Zip or City")),
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
        containerEl: t.any().optional(),
    });

    setup() {
        this.uiService = useService("ui");
        this.state = proxy({
            locations: [],
            viewMode: "list",
            zipCode: this.props.zipCode,
            selectedLocationId: "",
            isSmall: this.uiService.isSmall,
        });

        this.debouncedOnResize = useDebounced(this.updateSize.bind(this), 300);
        this.debouncedSearchButton = useDebounced(() => {
            this.state.locations = [];
            this.updateLocations(this.state.zipCode);
        }, 300);

        useListener(window, "resize", this.debouncedOnResize.bind(this));

        onMounted(() => {
            this.updateSize();
        });

        // Fetch new locations when the zip code is updated.
        useEffect(() => {
            this.updateLocations(this.state.zipCode);
        });
    }

    // This get can be overridden to filter the available locations
    // e.g.: website_sale_collects uses a filter based on country code
    get locations() {
        return this.state.locations;
    }

    /**
     * Update displayed locations based on the zip in the searchbar. Then, if
     * the old selected location is not anymore displayed, select the first
     * location in the list.
     *
     * @param {String} searchedZip - The zip code used to look for close locations.
     */
    async updateLocations(searchedZip) {
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
     */
    setSelectedLocation(locationId) {
        this.state.selectedLocationId = String(locationId);
    }

    /**
     * Set the visibleLocations in the state.
     *
     * @param {Array} locationsIds
     */
    setVisibleLocations(locationsIds) {
        if (this.props.hideOffscreenLocations) {
            this.state.visibleLocations = new Set(locationsIds);
        }
    }

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

    updateSize() {
        this.state.isSmall = this.uiService.isSmall;
    }
}
