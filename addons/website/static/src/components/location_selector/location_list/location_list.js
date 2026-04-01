import { useLayoutEffect } from "@web/owl2/utils";
import { Location } from "../location/location";
import { Component, onMounted } from "@odoo/owl";

export class LocationList extends Component {
    static components = { Location };
    static template = "website.locationSelector.locationList";
    static props = {
        hideOffscreenLocations: { type: Boolean, optional: true },
        locations: Array,
        selectedLocationId: [String, { value: false }],
        setSelectedLocation: Function,
        showIndexes: { type: Boolean, optional: true },
        showPinIndicator: { type: Boolean, optional: true },
        validateSelection: { type: Function, optional: true },
        visibleLocations: {
            type: Set,
            element: String,
            optional: true,
        },
    };
    static defaultProps = {
        hideOffscreenLocations: false,
        showIndexes: true,
        showPinIndicator: true,
        visibleLocations: new Set(),
    };

    setup() {
        onMounted(() => {
            document.getElementById(`location-${this.props.selectedLocationId}`)?.focus();
        });

        // Focus on the location on the list when clicking on the map marker.
        useLayoutEffect(
            (locations, selectedLocationId) => {
                const selectedLocation = locations.find((l) => String(l.id) === selectedLocationId);
                if (selectedLocation) {
                    document.getElementById(`location-${selectedLocation.id}`)?.focus();
                }
            },
            () => [this.props.locations, this.props.selectedLocationId]
        );
    }
}
