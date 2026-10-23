import { pick } from "@web/core/utils/objects";

// Optional partner fields. The page source contains an optional field only
// if its option is enabled.
export const STORE_LOCATOR_OPTIONAL_FIELDS = {
    mapShowEmail: "email",
    mapShowImage: "image_256",
    mapShowPhone: "phone",
    mapShowWebsite: "website",
};

// Fake data to mock the optional fields also on example locations.
const EXAMPLE_LOCATIONS_OPTIONAL_VALUES = {
    [-1]: {
        email: "store1@example.com",
        phone: "(603)-996-3829",
        website: "https://store1.example.com",
    },
    [-2]: {
        email: "store2@example.com",
        phone: "(870)-931-0505",
        website: "https://store2.example.com",
    },
};

/**
 * Get the optional fields that the enabled options show.
 *
 * @param {HTMLElement} editingElement the store locator snippet
 * @return {string[]} the names of the fields
 */
export function getEnabledOptionalFields(editingElement) {
    return Object.entries(STORE_LOCATOR_OPTIONAL_FIELDS)
        .filter(([datasetKey]) => editingElement.dataset[datasetKey] === "true")
        .map(([, field]) => field);
}

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

    /**
     * Read some fields of the partners and copy them to the locations.
     *
     * @param {Object} orm the ORM service
     * @param {Map<number, Object>} locationsMap the locations, by partner id
     * @param {number[]} idsToUpdate the ids of the partners to update
     * @param {string[]} fields the names of the fields to read
     */
    async readFields(orm, locationsMap, idsToUpdate, fields) {
        if (!fields.length || !idsToUpdate.length) {
            return;
        }
        const exampleIds = idsToUpdate.filter((id) => id < 0);
        const partnerIds = idsToUpdate.filter((id) => id > 0);
        for (const id of exampleIds) {
            const exampleValues = EXAMPLE_LOCATIONS_OPTIONAL_VALUES[id] || {};
            Object.assign(locationsMap.get(id), pick(exampleValues, ...fields));
        }
        if (partnerIds.length) {
            const partnersData = await orm.read("res.partner", partnerIds, fields);
            for (const partnerData of partnersData) {
                Object.assign(locationsMap.get(partnerData.id), partnerData);
            }
        }
    },
};
