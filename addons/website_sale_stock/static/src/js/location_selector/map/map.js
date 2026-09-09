/*global L*/

import { useLayoutEffect } from "@web/owl2/utils";
import { Component, onMounted, onWillUnmount, signal, t, useProps } from "@odoo/owl";
import { renderToString } from '@web/core/utils/render';

export class Map extends Component {
    static template = 'website_sale_stock.locationSelector.map';
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
    });

    mapRef = signal.ref();

    setup() {
        this.leafletMap = null;
        this.markers = [];

        // Create the map.
        onMounted(() => {
            this.leafletMap = L.map(this.mapRef(), {
                zoom: 13,
            });
            this.leafletMap.attributionControl.setPrefix(
                '<a href="https://leafletjs.com" title="A JavaScript library for interactive maps">Leaflet</a>'
            );
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: "&copy; <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>"
            }).addTo(this.leafletMap);
        });
        onWillUnmount(() => {
            this.leafletMap.remove();
        });

        // Update the size of the map.
        useLayoutEffect(
            (locations) => {
                this.leafletMap.invalidateSize();
            },
            () => [this.props.locations]
        );

        // Update the markers and center the map on the selected location.
        useLayoutEffect(
            (locations, selectedLocationId) => {
                this.addMarkers(locations);
                const selectedLocation = locations.find(
                    l => String(l.id) === selectedLocationId
                );
                if (selectedLocation) {
                    // Center the Map.
                    this.leafletMap.panTo(
                        [selectedLocation.latitude, selectedLocation.longitude],
                        { animate: true }
                    );
                }
                return () => {
                    this.removeMarkers();
                };
            },
            () => [this.props.locations, this.props.selectedLocationId]
        );
    }

    /**
     * Add the markers of the closest locations on the map.
     * Binds events to the created markers.
     *
     * @param {Array} locations - The list of locations to display on the map.
     * @return {void}
     */
    addMarkers(locations) {
        for (const loc of locations) {
            const isSelected = String(loc.id) === this.props.selectedLocationId
            // Icon creation
            const iconInfo = {
                className: isSelected ? 'o_location_selector_marker_icon_selected'
                    : 'o_location_selector_marker_icon',
                html: renderToString(
                    'website_sale_stock.locationSelector.map.marker',
                    { number: locations.indexOf(loc) + 1 },
                ),
                iconSize: [30, 40],
                iconAnchor: [15, 40],
            };

            const marker = L.marker(
                [loc.latitude, loc.longitude],
                {
                    icon: L.divIcon(iconInfo),
                    title: locations.indexOf(loc) + 1,
                },
            );

            // By default, the marker's zIndex is based on its latitude. This ensures the selected
            // marker is always displayed on top of all others.
            if (isSelected) marker.setZIndexOffset(100);

            marker.addTo(this.leafletMap);
            marker.addEventListener('click', () => {
                this.props.setSelectedLocation(loc.id);
            });

            this.markers.push(marker);
        }
    }

    /**
     * Remove the markers from the map and empty the markers array.
     *
     * @return {void}
     */
    removeMarkers() {
        for (const marker of this.markers) {
            marker.removeEventListener();
            this.leafletMap.removeLayer(marker);
        }
        this.markers = [];
    }

    /**
     * Find the selected location based on its id.
     *
     * @return {Object} The selected location.
     */
    get selectedLocation() {
        return this.props.locations.find(l => String(l.id) === this.props.selectedLocationId)
    }
}
