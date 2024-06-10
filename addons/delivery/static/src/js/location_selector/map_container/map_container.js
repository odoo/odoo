/** @odoo-module **/

import {
    LocationSchedule
} from '@delivery/js/location_selector/location_schedule/location_schedule';
import { Map } from '@delivery/js/location_selector/map/map';
import { Component, onWillStart, useState } from '@odoo/owl';
import { AssetsLoadingError, loadCSS, loadJS } from '@web/core/assets';

export class MapContainer extends Component {
    static components = { LocationSchedule, Map };
    static template = 'delivery.locationSelector.mapContainer';
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
                    state: { type: String, optional: true},
                    country_code: String,
                    additional_data: { type: Object, optional: true},
                    latitude: String,
                    longitude: String,
                }
            },
        },
        selectedLocationId: [String, {value: false}],
        setSelectedLocation: Function,
        validateSelection: Function,
    };

    setup() {
        this.state = useState({
            shouldLoadMap: false,
        });

        onWillStart(async () => {
            /**
             * We load the script for the map before rendering the owl component to avoid a
             * UserError if the script can't be loaded (e.g. if the customer loses the connection
             * between the rendering of the page and when he opens the location selector, or if the
             * CDN’s doesn't host the library anymore).
             */
            try {
                await Promise.all([
                    loadJS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'),
                    loadCSS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'),
                ])
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
        return this.props.locations.find(l => String(l.id) === this.props.selectedLocationId);
    }
}
