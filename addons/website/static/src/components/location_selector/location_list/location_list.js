import { useLayoutEffect } from "@web/owl2/utils";
import { Location } from "../location/location";
import { Component, onMounted, props, t } from "@odoo/owl";

export class LocationList extends Component {
    static components = { Location };
    static template = "website.locationSelector.locationList";
    props = props({
        hideOffscreenLocations: t.boolean().optional(false),
        locations: t.array(),
        selectedLocationId: t.string(),
        setSelectedLocation: t.function(),
        showIndexes: t.boolean().optional(true),
        showPinIndicator: t.boolean().optional(true),
        validateSelection: t.function().optional(),
        visibleLocations: t.instanceOf(Set).optional(new Set()),
    });
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
