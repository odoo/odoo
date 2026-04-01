import { LocationList } from "@website/components/location_selector/location_list/location_list";
import { MapContainer } from "@website/components/location_selector/map_container/map_container";
import { Component, onMounted, proxy, t, useListener, useOnChange, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { fuzzyLookup } from "@web/core/utils/search";

export class LocationSelectorComponent extends Component {
    static components = { LocationList, MapContainer };
    static template = "website.locationSelector.component";
    props = useProps({
        // This component can be overridden in other modules (see
        // `LocationSelectorDialog` in `website_sale_stock`). Some props here
        // are defined as optional and then exposed by a getter to facilitate
        // the override.
        mapZoom: t.string().optional(),
        showSidebar: t.boolean().optional(),
        showSearchbar: t.boolean().optional(),
        mapSearchbarPlaceholder: t.string().optional(_t("Zip or City")),
        sidebarLocation: t.string().optional(),
        showDetailsTooltip: t.boolean().optional(),
        showDetailsTextArea: t.boolean().optional(),
        hideOffscreenLocations: t.boolean().optional(false),
        locationsList: t.string().optional(),
        showEmail: t.boolean().optional(false),
        showImage: t.boolean().optional(false),
        showPhone: t.boolean().optional(false),
        showWebsite: t.boolean().optional(false),
        zipCode: t.string().optional(),
    });

    // The following getters are defined to facilitate the overriding of the
    // component (see`LocationSelectorDialog` in `website_sale_stock`).
    get mapZoom() {
        return this.props.mapZoom;
    }

    get showSidebar() {
        return this.props.showSidebar ?? false;
    }

    get showSearchbar() {
        return this.props.showSearchbar ?? false;
    }

    get sidebarLocation() {
        return this.props.sidebarLocation;
    }

    get showDetailsTooltip() {
        return this.props.showDetailsTooltip;
    }

    get showDetailsTextArea() {
        return this.props.showDetailsTextArea;
    }

    get showIndexes() {
        return false;
    }

    get showPinIndicator() {
        return false;
    }

    get showLocationNameOnMarkerHover() {
        return true;
    }

    get pressControlToZoom() {
        return true;
    }

    get validateSelection() {
        return undefined;
    }

    setup() {
        this.uiService = useService("ui");
        this.state = proxy({
            locations: [],
            viewMode: "list",
            searchQuery: this.props.zipCode,
            selectedLocationId: "",
            isSmall: this.uiService.isSmall,
        });

        this.debouncedOnResize = useDebounced(this.updateSize.bind(this), 300);
        this.debouncedSearchButton = useDebounced(() => {
            this.updateLocations(this.state.searchQuery);
        }, 300);

        useListener(window, "resize", this.debouncedOnResize.bind(this));

        onMounted(this.updateSize);

        // `useEffect` is not used here because it runs synchronously during
        // `setup`, before an overriding `setup` (e.g. in `LocationSelectorDialog`)
        // gets a chance to finish updating `this.state`.
        onMounted(() => this.updateLocations(this.state.searchQuery));
        useOnChange(
            () => [this.state.searchQuery],
            () => this.updateLocations(this.state.searchQuery),
            { initialRun: false }
        );
    }

    // This get can be overridden to filter the available locations
    // e.g.: website_sale_collects uses a filter based on country code
    get locations() {
        return this.state.locations;
    }

    /**
     * Update displayed locations based on the query in the searchbar. Then, if
     * the old selected location is not anymore displayed, select the first
     * location in the list.
     *
     * @param {String} searchQuery - The searched string
     */
    updateLocations(searchQuery) {
        const allLocations = JSON.parse(this.props.locationsList || "[]");

        const searchResult = searchQuery
            ? fuzzyLookup(searchQuery, allLocations, (location) => [location.city, location.zip])
            : allLocations;

        this.state.locations = searchResult.map(
            ({ partner_latitude, partner_longitude, zip, ...rest }) => ({
                ...rest,
                zip_code: zip,
                latitude: partner_latitude,
                longitude: partner_longitude,
            })
        );
        if (!this.state.locations.some((l) => String(l.id) === this.state.selectedLocationId)) {
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
        if (!this.showSidebar || this.state.viewMode === "map") {
            return MapContainer;
        }
        return LocationList;
    }

    updateSize() {
        this.state.isSmall = this.uiService.isSmall;
    }
}
