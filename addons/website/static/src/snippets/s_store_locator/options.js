import options from "@web_editor/js/editor/snippets.options";

options.registry.StoreLocator = options.Class.extend({
    init() {
        this._super(...arguments);
        this.http = this.bindService("http");
        this.orm = this.bindService("orm");
        this.init = true;
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
     * Adds every selected location and its data as an attribute
     */
    renderListItems(previewMode, widgetValue, params) {
        const locationsData = [];
        if (widgetValue) {
            const selectedIds = JSON.parse(widgetValue).map(({ id }) => id);
            for (const record of JSON.parse(params.availableRecords).filter(({ id }) =>
                selectedIds.includes(id)
            )) {
                const locationData = {
                    id: record.id,
                    name: record.display_name,
                    street: record.street,
                    city: record.city,
                    zip_code: record.zip_code,
                    latitude: record.partner_latitude,
                    longitude: record.partner_longitude,
                    opening_hours: record.opening_hours,
                };
                locationsData.push(locationData);
            }
        }
        this.$target[0].setAttribute("locations_data", JSON.stringify(locationsData));
    },

    async refreshGeoloc(previewMode, widgetValue, params) {
        await this._updateAvailableRecords(this.el.querySelector("div.o_we_m2m"), true);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === "renderListItems") {
            if (this.init) {
                //Initializes with previously selected locations
                const locations = [];
                const locationData = this.$target[0].attributes["locations_data"]?.nodeValue;
                if (locationData) {
                    JSON.parse(params.availableRecords).map((record) => {
                        if (
                            JSON.parse(locationData)
                                ?.map(({ id }) => id)
                                .includes(record.id)
                        ) {
                            locations.push(record);
                        }
                    });
                }
                this.init = false;
                return JSON.stringify(locations);
            } else if (params.activeValue) {
                return params.activeValue;
            } else {
                return JSON.stringify([]);
            }
        }
        return this._super(...arguments);
    },

    /*
     * Fetches every res.partner that is a company
     * If the stock module is installed also fetches the opening hours for each shop that has them
     */
    async _fetchLocations() {
        const storeLocations = [];
        await this.orm
            .searchRead(
                "res.partner",
                [
                    ["is_company", "=", "true"],
                    ["commercial_company_name", "not in", ["", null]],
                    ["street", "not in", ["", null]],
                    ["city", "not in", ["", null]],
                    ["zip", "not in", ["", null]],
                    ["contact_address_complete", "not in", ["", null]],
                ],
                [
                    "commercial_company_name",
                    "street",
                    "city",
                    "zip",
                    "partner_latitude",
                    "partner_longitude",
                    "phone",
                    "email",
                ]
            )
            .then(function (values) {
                for (const value of values) {
                    storeLocations.push({
                        id: value.id,
                        display_name: value.commercial_company_name,
                        street: value.street,
                        city: value.city,
                        zip_code: value.zip,
                        partner_latitude: value.partner_latitude,
                        partner_longitude: value.partner_longitude,
                        phone: value.phone,
                        email: value.email,
                        opening_hours: {},
                    });
                }
            });
        if (
            (
                await this.orm.search("ir.module.module", [
                    ["name", "=", "website_sale_collect"],
                    ["state", "=", "installed"]
                ])
            ).length > 0
        ) {
            var opening_hours_formats = [];
            const weekArrayStructure = {
                0: [],
                1: [],
                2: [],
                3: [],
                4: [],
                5: [],
                6: [],
            };
            await this.orm
                .searchRead(
                    "resource.calendar.attendance",
                    [["day_period", "!=", "lunch"]],
                    ["calendar_id", "dayofweek", "day_period", "hour_from", "hour_to"]
                )
                .then(function (values) {
                    for (
                        var i = 0;
                        i <=
                        values
                            .map(({ calendar_id }) => calendar_id[0])
                            .reduce((max, curr) => (curr > max ? curr : max), 0);
                        i++
                    ) {
                        opening_hours_formats.push(weekArrayStructure);
                    }
                    for (const value of values) {
                        var hoursFromConverter = new Date(0);
                        var hoursToConverter = new Date(0);
                        hoursFromConverter.setSeconds(value.hour_from * 3600);
                        hoursToConverter.setSeconds(value.hour_to * 3600);
                        opening_hours_formats[value.calendar_id[0]][value.dayofweek][value.day_period == "morning" ? 0 : 1] =
                            hoursFromConverter.toISOString().substring(11, 16) +
                            " - " +
                            hoursToConverter.toISOString().substring(11, 16);
                    }
                });
            await this.orm
                .searchRead("stock.warehouse", [], ["partner_id", "opening_hours"])
                .then(function (values) {
                    for (const value of values) {
                        for (var location of storeLocations) {
                            if (location.id == value.partner_id[0]) {
                                location.opening_hours = opening_hours_formats[value.opening_hours[0]];
                            }
                        }
                    }
                });
        }
        return storeLocations;
    },

    /*
     * Uses the OpenStreetMap API to fetch the store coordinates and saves them to DB
     */
    async _fetchGeoLoc(locations, forceNew = false) {
        for (const location of locations) {
            if (forceNew || !location["partner_latitude"] || !location["partner_longitude"]) {
                const addr = encodeURIComponent(
                    (
                        location["street"] +
                        " " +
                        location["city"] +
                        " " +
                        location["zip_code"]
                    ).replace(/[/,]/g, " ")
                );
                const response = await this.http.get(
                    `https://nominatim.openstreetmap.org/search?q=${addr}&format=jsonv2`
                );
                if (response[0]) {
                    location["partner_latitude"] = parseFloat(response[0]["lat"]);
                    location["partner_longitude"] = parseFloat(response[0]["lon"]);
                    this.orm.write("res.partner", [location.id], {
                        partner_latitude: location["partner_latitude"],
                        partner_longitude: location["partner_longitude"],
                    });
                }
            }
        }
    },

    async _updateAvailableRecords(m2mEl, forceNewGeoloc = false) {
        var records = await this._fetchLocations();
        await this._fetchGeoLoc(records, forceNewGeoloc);
        m2mEl.dataset.availableRecords = JSON.stringify(records);
    },

    /**
     * @override
     */
    _renderCustomXML: async function (uiFragment) {
        const m2mEl = uiFragment.querySelector("we-many2many");
        await this._updateAvailableRecords(m2mEl);
    },
});

export default {
    StoreLocator: options.registry.StoreLocator,
};
