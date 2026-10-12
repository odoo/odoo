import { useLayoutEffect } from "@web/owl2/utils";
import { Location } from '@website_sale_stock/js/location_selector/location/location';
import { Component, onMounted, t, useProps } from '@odoo/owl';

export class LocationList extends Component {
    static components = { Location };
    static template = 'website_sale_stock.locationSelector.locationList';
    props = useProps({
        locations: t.array(t.object({
            id: t.or([t.string(), t.number()]),
            name: t.string(),
            opening_hours: t.record(t.array(t.string())),
            street: t.string(),
            city: t.string(),
            zip_code: t.string(),
            state: t.string().optional(),
            country_code: t.string(),
            additional_data: t.object().optional(),
            distance: t.number().optional(),
            latitude: t.or([t.string(), t.number()]),
            longitude: t.or([t.string(), t.number()]),
        })),
        selectedLocationId: t.or([t.string(), t.literal(false)]),
        setSelectedLocation: t.function(),
        validateSelection: t.function(),
    });

    setup() {
        onMounted(() => {
            document.getElementById(`location-${this.props.selectedLocationId}`)?.focus();
        });

        // Focus on the location on the list when clicking on the map marker.
        useLayoutEffect(
            (locations, selectedLocationId) => {
                const selectedLocation = locations.find(
                    l => String(l.id) === selectedLocationId
                );
                if (selectedLocation) {
                    document.getElementById(`location-${selectedLocation.id}`).focus();
                }
            },
            () => [this.props.locations, this.props.selectedLocationId]
        );
    }
}
