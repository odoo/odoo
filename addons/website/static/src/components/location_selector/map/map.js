/*global L*/

import { Component, useEffect, useRef } from "@odoo/owl";
import { renderToString } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";

const OSM_MAX_ZOOM = 19;

export class Map extends Component {
    static template = "website.locationSelector.map";
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
                    state: { type: String, optional: true },
                    country_code: String,
                    additional_data: { type: Object, optional: true },
                    latitude: String,
                    longitude: String,
                },
            },
        },
        pressControlToZoom: { type: Boolean, optional: true },
        selectedLocationId: [String, { value: false }],
        setSelectedLocation: Function,
        setVisibleLocations: Function,
        showDetailsTooltip: Boolean,
        showIndexes: Boolean,
        showEmail: Boolean,
        showImage: Boolean,
        showPhone: Boolean,
        showWebsite: Boolean,
        showLocationNameOnMarkerHover: { type: Boolean, optional: true },
        mapZoom: String,
    };

    setup() {
        this.leafletMap = null;
        this.markers = [];
        this.mapRef = useRef("map");

        // Create the map.
        useEffect(
            () => {
                this.leafletMap = L.map(this.mapRef.el, {
                    zoom: parseInt(this.props.mapZoom),
                });
                this.leafletMap.attributionControl.setPrefix(
                    '<a href="https://leafletjs.com" title="A JavaScript library for interactive maps">Leaflet</a>'
                );

                L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                    maxZoom: OSM_MAX_ZOOM,
                    attribution:
                        "&copy; <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>",
                }).addTo(this.leafletMap);

                this.leafletMap.addEventListener("moveend", () => {
                    this.props.setVisibleLocations?.(this.getVisibleMarks(this.leafletMap));
                });

                if (this.props.pressControlToZoom) {
                    this.mapRef.el.dataset.zoomDisabledText = _t("Hold Ctrl and scroll to zoom");
                    this.leafletMap.scrollWheelZoom.disable();
                    this.leafletMap.getContainer().addEventListener("wheel", (e) => {
                        if (e.metaKey || e.ctrlKey) {
                            e.preventDefault();
                            this.mapRef.el.classList.remove("map_zoom_disabled");
                            this.leafletMap.scrollWheelZoom.enable();
                            clearTimeout(this.zoomDisabledWarning);
                        } else {
                            this.leafletMap.scrollWheelZoom.disable();
                            this.mapRef.el.classList.add("map_zoom_disabled");
                            this.zoomDisabledWarning = setTimeout(() => {
                                this.mapRef.el.classList.remove("map_zoom_disabled");
                            }, 3000);
                        }
                    });
                }

                return () => {
                    this.leafletMap.remove();
                };
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
                const selectedLocation = locations.find((l) => String(l.id) === selectedLocationId);
                if (selectedLocation) {
                    // Center the Map.
                    this.leafletMap.panTo([selectedLocation.latitude, selectedLocation.longitude], {
                        animate: true,
                    });
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
            const isSelected = String(loc.id) === this.props.selectedLocationId;
            // Icon creation
            const iconInfo = {
                className: isSelected
                    ? "o_location_selector_marker_icon_selected"
                    : "o_location_selector_marker_icon",
                html: renderToString("website.locationSelector.map.marker", {
                    number: this.props.showIndexes && locations.indexOf(loc) + 1,
                }),
                iconSize: [30, 40],
                iconAnchor: [15, 40],
            };

            const marker = L.marker([loc.latitude, loc.longitude], {
                icon: L.divIcon(iconInfo),
                title: this.props.showLocationNameOnMarkerHover
                    ? loc.name
                    : locations.indexOf(loc) + 1,
            });
            marker.id = locations.indexOf(loc) + 1;

            // By default, the marker's zIndex is based on its latitude. This ensures the selected
            // marker is always displayed on top of all others.
            if (isSelected) {
                marker.setZIndexOffset(100);
                if (this.props.showDetailsTooltip) {
                    marker.bindTooltip(
                        renderToString("website.locationSelector.map.tooltip", {
                            location: loc,
                            showEmail: this.props.showEmail,
                            showPhone: this.props.showPhone,
                            showWebsite: this.props.showWebsite,
                        }),
                        {
                            direction: "bottom",
                            permanent: "true",
                        }
                    );
                }
            }

            marker.addTo(this.leafletMap);
            marker.addEventListener("click", () => {
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
            marker.unbindTooltip();
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
        return this.props.locations.find((l) => String(l.id) === this.props.selectedLocationId);
    }

    /**
     * Find the locations placed outside the portion of the map currently in view.
     *
     * @return {Array} The list of hidden markers
     */
    getVisibleMarks() {
        const map = this.leafletMap;
        const visibleMarks = [];
        map.eachLayer(function (layer) {
            if (layer instanceof L.Marker) {
                if (map.getBounds().contains(layer.getLatLng())) {
                    visibleMarks.push(String(layer.id));
                }
            }
        });
        return visibleMarks;
    }
}
