import { Location } from '@website_sale_stock/js/location_selector/location/location';
import { Component, onMounted, useEffect } from '@odoo/owl';

export class LocationList extends Component {
    static components = { Location };
    static template = 'website_sale_stock.locationSelector.locationList';
    static props = {
        locations: {
            type: Array,
            element: {
                type: Object,
                values: {
                    type: Object,
                    shape: {
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
                        zip_code: String,
                        state: { type: String, optional: true },
                        country_code: String,
                        additional_data: { type: Object, optional: true },
                        latitude: String,
                        longitude: String,
                    },
                },
            },
        },
        selectedLocationId: [String, { value: false }],
        setSelectedLocation: Function,
        validateSelection: Function,
    };

    setup() {
        onMounted(() => {
            document.getElementById(`location-${this.props.selectedLocationId}`)?.focus();
        });

        // Focus on the location on the list when clicking on the map marker.
        useEffect(() => {
            void this.props.locations;
            void this.props.selectedLocationId;
            const selectedLocation = this.props.locations.find(
                (l) => String(l.id) === this.props.selectedLocationId
            );
            if (selectedLocation) {
                document.getElementById(`location-${selectedLocation.id}`)?.focus();
            }
        });
    }
}
