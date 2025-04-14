import { StoreLocatorLocation } from '@website/components/store_locator_map/store_locator_location';
import { Component, onMounted, useEffect } from '@odoo/owl';

export class StoreLocatorLocationList extends Component {
    static components = { StoreLocatorLocation };
    static template = 'website.store_locator_location_list';
    static props = {
        locations: {
            type: Array,
            element: {
                type: Object,
                values: {
                    id: String,
                    name: String,
                    openingHours: {
                        type: Object,
                        values: {
                            type: Array,
                            element: String,
                            optional: true,
                        },
                    },
                    street: String,
                    city: String,
                    zip: String,
                    state: { type: String, optional: true},
                    country_code: String,
                    additional_data: { type: Object, optional: true},
                    partner_latitude: String,
                    partner_longitude: String,
                }
            },
        },
        selectedLocationId: [String, {value: false}],
        setSelectedLocation: Function,
        validateSelection: Function,
        hiddenLocations: {
            type: Array,
            element: String,
        },
    };

    setup() {
        onMounted(() => {
            document.getElementById(`location-${this.props.selectedLocationId}`).focus();
        });

        // Focus on the location on the list when clicking on the map marker.
        useEffect(
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
