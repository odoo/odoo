import {
    LocationSchedule,
    getTodayStatus,
} from '@website_sale_stock/js/location_selector/location_schedule/location_schedule';
import { Component, t, useProps } from '@odoo/owl';

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
        hoveredLocationId: t.function().optional(),
        setSelectedLocation: t.function(),
        validateSelection: t.function(),
        readonly: t.boolean().optional(),
    });

    /**
     * Get the city and the zip code.
     *
     * @return {Object} The city and the zip code.
     */
    getCityAndZipCode() {
        return `${this.props.zipCode} ${this.props.city}`;
    }

    get hasOpeningHours() {
        return Object.keys(this.props.openingHours).length > 0;
    }

    get isHovered() {
        return !this.props.readonly && this.props.hoveredLocationId?.() === this.props.id;
    }

    get todayStatus() {
        return getTodayStatus(this.props.openingHours);
    }

    /**
     * Select this location and confirm it.
     *
     * @return {void}
     */
    async chooseLocation() {
        this.props.setSelectedLocation(this.props.id);
        await this.props.validateSelection();
    }
}
