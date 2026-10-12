import {
    LocationSchedule
} from '@website_sale_stock/js/location_selector/location_schedule/location_schedule';
import { Component, t, useProps } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';

export class Location extends Component {
    static components = { LocationSchedule };
    static template = 'website_sale_stock.locationSelector.location';
    props = useProps({
        id: t.string(),
        number: t.number(),
        name: t.string(),
        street: t.string(),
        city: t.string(),
        zipCode: t.string(),
        openingHours: t.record(t.array(t.string()).optional()),
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
