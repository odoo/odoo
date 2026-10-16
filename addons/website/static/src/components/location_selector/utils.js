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
