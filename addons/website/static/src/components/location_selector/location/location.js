import { LocationSchedule } from "@website/components/location_selector/location_schedule/location_schedule";
import { Component, props, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class Location extends Component {
    static components = { LocationSchedule };
    static template = "website.locationSelector.location";
    props = props({
        id: t.string(),
        number: t.number().optional(),
        name: t.string(),
        city: t.string(),
        zipCode: t.string(),
        openingHours: t.object({ value: t.array(t.string()) }).optional({}),
        isSelected: t.boolean(),
        setSelectedLocation: t.function(),
        showPinIndicator: t.boolean().optional(true),
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
