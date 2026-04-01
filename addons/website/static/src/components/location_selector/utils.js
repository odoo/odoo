import { t } from "@odoo/owl";

const LOCATION = t.object({
    id: t.or([t.string(), t.number()]),
    name: t.string(),
    opening_hours: t.object().optional({}),
    street: t.string(),
    city: t.string(),
    zip_code: t.string(),
    state: t.string().optional(),
    country_code: t.or([t.string(), t.array(t.or([t.number(), t.string()]))]),
    additional_data: t.object().optional({}),
    distance: t.number().optional(),
    latitude: t.or([t.string(), t.number()]),
    longitude: t.or([t.string(), t.number()]),
});

export const LOCATION_LIST = t.array(LOCATION);

/**
 * Get the street, the zip code and the city on a single line.
 *
 * @param {Object} location - The location from which the address is taken.
 * @return {String} The full address.
 */
export function getFullAddress(location) {
    return [location.street, `${location.zip_code} ${location.city}`.trim()]
        .filter(Boolean)
        .join(", ");
}
