/** @odoo-module native */
import { LocationSchedule } from "@delivery/js/location_selector/location_schedule/location_schedule";
import { Map } from "@delivery/js/location_selector/map/map";
import { Component, useState } from "@odoo/owl";
import { AssetsLoadingError, loadCSS, loadJS } from "@web/core/assets";
import { _t } from "@web/core/translation";

export class MapContainer extends Component {
    static components = { LocationSchedule, Map };
    static template = "delivery.locationSelector.mapContainer";
    static props = {
        locations: {
            type: Array,
            element: {
                type: Object,
                values: {
                    id: String,
                    name: String,
                    openingHours: {
                        type: Object,
                        values: {
                            type: Array,
                            element: String,
                            optional: true,
                        },
                    },
                    street: String,
                    city: String,
                    zip_code: String,
                    state: { type: String, optional: true },
                    country_code: String,
                    additional_data: { type: Object, optional: true },
                    latitude: String,
                    longitude: String,
                },
            },
        },
        selectedLocationId: [String, { value: false }],
        setSelectedLocation: Function,
        validateSelection: Function,
    };

    setup() {
        this.state = useState({ mapStatus: "loading" });
        // The dialog does not wait for the library: loadJS retries an unreachable CDN for
        // more than twenty seconds before it gives up, and the list and the selected
        // location's details are usable without the map.
        Promise.all([
            loadJS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"),
            loadCSS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"),
        ]).then(
            () => {
                this.state.mapStatus = "loaded";
            },
            (error) => {
                if (!(error instanceof AssetsLoadingError)) {
                    throw error;
                }
                this.state.mapStatus = "failed";
            },
        );
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
        return this.props.locations.find(
            (l) => String(l.id) === this.props.selectedLocationId,
        );
    }

    get errorMessage() {
        return _t("There was an error loading the map");
    }

    get chooseLocationButtonLabel() {
        return _t("Choose this location");
    }

    get openingHoursLabel() {
        return _t("Opening hours");
    }
}
