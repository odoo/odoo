import { LocationSchedule } from "../location_schedule/location_schedule";
import { Map } from "../map/map";
import { Component, onWillStart, props, proxy, t } from "@odoo/owl";
import { AssetsLoadingError, loadCSS, loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class MapContainer extends Component {
    static components = { LocationSchedule, Map };
    static template = "website.locationSelector.mapContainer";
    props = props({
        locations: t.array(),
        pressControlToZoom: t.boolean().optional(false),
        selectedLocationId: t.string(),
        setSelectedLocation: t.function(),
        setVisibleLocations: t.function().optional(),
        validateSelection: t.function().optional(),
        showDetailsTooltip: t.boolean().optional(false),
        showDetailsTextArea: t.boolean().optional(true),
        mapZoom: t.string().optional("13"),
        showIndexes: t.boolean(),
        showEmail: t.boolean().optional(false),
        showImage: t.boolean().optional(false),
        showPhone: t.boolean().optional(false),
        showWebsite: t.boolean().optional(false),
        showLocationNameOnMarkerHover: t.boolean().optional(false),
        containerEl: t.instanceOf(HTMLElement).optional(),
    });

    setup() {
        this.state = proxy({
            shouldLoadMap: false,
        });

        onWillStart(async () => {
            /**
             * We load the script for the map before rendering the owl component to avoid a
             * UserError if the script can't be loaded (e.g. if the customer loses the connection
             * between the rendering of the page and when he opens the location selector, or if the
             * CDN’s doesn't host the library anymore).
             * loadCSS's targetDoc option is needed when the component is mounted inside an iframe,
             * for example in website snippet selector (when browsing custom snippets).
             */
            try {
                await Promise.all([
                    loadJS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"),
                    loadCSS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", {
                        targetDoc: this.props.containerEl?.ownerDocument,
                    }),
                ]);
                this.state.shouldLoadMap = true;
            } catch (error) {
                if (!(error instanceof AssetsLoadingError)) {
                    throw error;
                }
            }
        });
    }

    /**
     * Get the city and the zip code.
     *
     * @param {Number} selectedLocation - The location form which the city and the zip code
     *                                    should be taken.
     * @return {Object} The city and the zip code.
     */
    getCityAndZipCode(selectedLocation) {
        return `${selectedLocation.zip_code} ${selectedLocation.city}`;
    }

    /**
     * Find the selected location based on its id.
     *
     * @return {Object} The selected location.
     */
    get selectedLocation() {
        return this.props.locations.find((l) => String(l.id) === this.props.selectedLocationId);
    }

    get errorMessage() {
        return _t("There was an error loading the map");
    }

    get chooseLocationButtonLabel() {
        return _t("Choose this location");
    }

    get hasOpeningHours() {
        return (
            this.selectedLocation.opening_hours &&
            Object.keys(this.selectedLocation.opening_hours).length > 0
        );
    }

    get openingHoursLabel() {
        return _t("Opening hours");
    }
}
