import { _t } from "@web/core/l10n/translation";
import options from '@web_editor/js/editor/snippets.options';
import { rpc } from '@web/core/network/rpc';


let init = true;
let dbStoreLocations;
let dbStoreLocationsProm;
const cleardbStoreLocationsCache = () => {
    dbStoreLocationsProm = undefined;
    dbStoreLocations = undefined;
};
const getdbStoreLocationsCache = () => {
    return dbStoreLocations;
};

options.registry.StoreLocator = options.Class.extend({
    /**
     * @override
     */
    async onBuilt() {
    },

    init() {
        this._super(...arguments);
        this.http = this.bindService('http');
    },

    /**
     * @override
     */
    start() {
        return this._super(...arguments);
    },

    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
    },

    /**
     * Adds every selected location and its data to the DOM as <i> elements to be read by the StoreLocatorMap component
     */
    renderListItems(previewMode, widgetValue, params) {
        const locationsData = [];
        JSON.parse(params.availableRecords).map((record) => {
            if(JSON.parse(widgetValue).map(({id}) => id).includes(record.id)) {
                const locationData = {
                    id: record.id,
                    name: record.display_name,
                    opening_hours: {},
                    street: record.street,
                    city: record.city,
                    zip_code: record.zip_code,
                    latitude: record.latitude,
                    longitude: record.longitude,
                    // phone: record.phone,
                    // email: record.email,
                    // locationElem.setAttribute("opening_hours", record.opening_hours);
                }
                locationsData.push(locationData);
            }
        });
        this.$target[0].setAttribute("locations_data", JSON.stringify(locationsData));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'renderListItems') {
            if(this.init) {
                //Initializes with previously selected locations
                const locations = [];
                const locationData = this.$target[0].attributes['locations_data']?.nodeValue;
                if(locationData) {
                    JSON.parse(params.availableRecords).map((record) => {
                        if(JSON.parse(locationData)?.map(({id}) => id).includes(record.id)) {
                            locations.push(record);
                        }
                    });
                }
                this.init = false;
                return JSON.stringify(locations);
            } else if(params.activeValue) {
                return params.activeValue;
            } else {
                return JSON.stringify([]);
            }
        }
        return this._super(...arguments);
    },

    /**
     *
     */
    async _fetchLocations() {
        if (!dbStoreLocationsProm) {
            dbStoreLocations = [];
            dbStoreLocationsProm = rpc('/website/get_locations').then(function (values) {
                for (let value of values) {
                    dbStoreLocations.push({
                        id: value.id,
                        display_name: value.commercial_company_name,
                        street: value.street,
                        city: value.city,
                        zip_code: value.zip,
                        latitude: value.partner_latitude,
                        longitude: value.partner_longitude,
                        phone: value.phone,
                        email: value.email,
                        // opening_hours: value.opening_hours,
                    });
                }
            });
        }
        await dbStoreLocationsProm;
    },

    async _fetchGeoLoc(locations) {
        for (let location of locations) {
            const addr = location['street'] + " " + location['city'] + " " + location['zip_code'];
            const response = await this.http.get("https://nominatim.openstreetmap.org/search?q=" + addr + "&format=jsonv2");
            if (response) {
                location['latitude'] = float(response[0]['lat'])
                location['longitude'] = float(response[0]['lon'])
            }
        }
    },

    /**
     * @override
     */
    _renderCustomXML: async function (uiFragment) {
        const m2mEl = uiFragment.querySelector("we-many2many");
        if(!dbStoreLocations) {
            await this._fetchLocations();
        }
        m2mEl.dataset.availableRecords = JSON.stringify(dbStoreLocations);
    },
});

export default {
    StoreLocator: options.registry.StoreLocator,
    cleardbStoreLocationsCache,
    getdbStoreLocationsCache,
};
