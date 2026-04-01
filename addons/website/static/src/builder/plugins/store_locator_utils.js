export const locationBatchUtils = {
    /**
     * Update the coordinates of the locations.
     *
     * @param {Object} orm the ORM service
     * @param {Map<number, Object>} locationsMap the locations, by partner id
     * @param {number[]} idsToUpdate the ids of the partners to update
     */
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

    /**
     * Update the opening hours of the locations.
     *
     * This method does nothing. The website_sale_collect module patches it,
     * because that module gives the opening hours.
     *
     * @param {Object} _orm the ORM service
     * @param {Map<number, Object>} _locationsMap the locations, by partner id
     * @param {number[]} _idsToUpdate the ids of the partners to update
     */
    async updateCalendar(_orm, _locationsMap, _idsToUpdate) {},
};
