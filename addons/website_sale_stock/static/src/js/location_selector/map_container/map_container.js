import {
    LocationSchedule
} from '@website_sale_stock/js/location_selector/location_schedule/location_schedule';
import { Map } from '@website_sale_stock/js/location_selector/map/map';
import { Component, onWillStart, proxy, t, useProps } from '@odoo/owl';
import { AssetsLoadingError, loadCSS, loadJS } from '@web/core/assets';
import { _t } from '@web/core/l10n/translation';

export class MapContainer extends Component {
    static components = { LocationSchedule, Map };
    static template = 'website_sale_stock.locationSelector.mapContainer';
    props = useProps({
        locations: t.array(t.object({
            id: t.or([t.string(), t.number()]),
            name: t.string(),
            opening_hours: t.record(t.array(t.string())),
            street: t.string(),
            city: t.string(),
            zip_code: t.string(),
            state: t.string().optional(),
            country_code: t.string(),
            additional_data: t.object().optional(),
            distance: t.number().optional(),
            latitude: t.or([t.string(), t.number()]),
            longitude: t.or([t.string(), t.number()]),
        })),
        selectedLocationId: t.or([t.string(), t.literal(false)]),
        setSelectedLocation: t.function(),
        validateSelection: t.function(),
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
