export const locationBatchUtils = {
    async geolocalize(orm, locationsMap, idsToUpdate) {
        // Calls geo_localize to update the coordinates of the partners
        await orm.call("res.partner", "geo_localize", [idsToUpdate]);
        // Reads the new coordinates and copies them to the locations, replacing
        // the old coordinates
        const coordinatesData = await orm.read("res.partner", idsToUpdate, [
            "partner_latitude",
            "partner_longitude",
        ]);
        coordinatesData.forEach((location) => {
            const loc = locationsMap.get(location.id);
            loc.partner_latitude = location.partner_latitude;
            loc.partner_longitude = location.partner_longitude;
        });
    },

    async updateCalendar(orm, locationsMap, idsToUpdate) {
        // This method is patched by website_sale_collect, as opening hours
        // are provided by this module.
    },
};
