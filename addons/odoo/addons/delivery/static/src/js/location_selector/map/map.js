/** @odoo-module **/
/*global L*/

import { Component, useEffect, useRef } from '@odoo/owl';
import { renderToString } from '@web/core/utils/render';

export class Map extends Component {
    static template = 'delivery.locationSelector.map';
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
                    zip_code: String,
                    state: { type: String, optional: true},
                    country_code: String,
                    additional_data: { type: Object, optional: true},
                    latitude: String,
                    longitude: String,
                }
            },
        },
        selectedLocationId: [String, {value: false}],
        setSelectedLocation: Function,
    };

    setup() {
        this.leafletMap = null;
        this.markers = [];
        this.mapRef = useRef('map');

        // Create the map.
        useEffect(
            () => {
                this.leafletMap = L.map(this.mapRef.el, {
                    zoom: 13,
                });
                this.leafletMap.attributionControl.setPrefix(
                    '<a href="https://leafletjs.com" title="A JavaScript library for interactive maps">Leaflet</a>'
                );
                L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: "&copy; <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>"
                }).addTo(this.leafletMap);
                return () => {
                    this.leafletMap.remove();
                }
            },
            () => []
        );

        // Update the size of the map.
        useEffect(
            (locations) => {
                this.leafletMap.invalidateSize();
            },
            () => [this.props.locations]
        );

        // Update the markers and center the map on the selected location.
        useEffect(
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
                    'delivery.locationSelector.map.marker',
                    { number: locations.indexOf(loc) + 1 },
                ),
                iconSize: [30, 40],
                iconAnchor: [15, 40],
            };

            const marker = L.marker(
                [ loc.latitude, loc.longitude ],
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
