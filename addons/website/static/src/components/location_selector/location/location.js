import { LocationSchedule } from "@website/components/location_selector/location_schedule/location_schedule";
import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class Location extends Component {
    static components = { LocationSchedule };
    static template = "website.locationSelector.location";
    props = useProps({
        additionalData: t.object().optional(),
        id: t.string(),
        number: t.or([t.number(), t.string()]),
        name: t.string(),
        street: t.string(),
        city: t.string(),
        zipCode: t.string(),
        openingHours: t.record(t.array(t.string()).optional()).optional({}),
        additionalData: t.object().optional(),
        isSelected: t.boolean(),
        setSelectedLocation: t.function(),
    });

    /**
     * Get the city and the zip code.
     *
     * @return {Object} The city and the zip code.
     */
    getCityAndZipCode() {
        return `${this.props.zipCode} ${this.props.city}`;
    }

    get openingHoursLabel() {
        return _t("Opening hours");
    }
}
