/*global L*/

import { Map } from "@delivery/js/location_selector/map/map";
import { patch } from "@web/core/utils/patch";
import { renderToString } from "@web/core/utils/render";
import { useEffect, useRef } from "@odoo/owl";

patch(Map.prototype, {
    setup() {
        this.leafletMap = null;
        this.markers = [];
        this.mapRef = useRef("map");

        // Create the satellite map.
        useEffect(
            () => {
                this.leafletMap = L.map(this.mapRef.el, {
                    zoom: this.__owl__.parent.parent.props.zoom
                        ? parseInt(this.__owl__.parent.parent.props.zoom)
                        : 12,
                });
                this.leafletMap.attributionControl.setPrefix(
                    '<a href="https://leafletjs.com" title="A JavaScript library for interactive maps">Leaflet</a>'
                );
                const maxZoom = 19;
                const attribution =
                    "&copy; <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>";

                if (this.__owl__.parent.parent.props.type == "Satellite") {
                    L.tileLayer("http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", {
                        maxZoom: maxZoom,
                        subdomains: ["mt0", "mt1", "mt2", "mt3"],
                        attribution: attribution,
                    }).addTo(this.leafletMap);
                } else {
                    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                        maxZoom: maxZoom,
                        attribution: attribution,
                    }).addTo(this.leafletMap);
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
    },

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
                html: renderToString("delivery.locationSelector.map.marker", {
                    number: locations.indexOf(loc) + 1,
                }),
                iconSize: [30, 40],
                iconAnchor: [15, 40],
            };

            const marker = L.marker([loc.latitude, loc.longitude], {
                icon: L.divIcon(iconInfo),
                title: locations.indexOf(loc) + 1,
            });

            // By default, the marker's zIndex is based on its latitude. This ensures the selected
            // marker is always displayed on top of all others.
            if (isSelected) {
                marker.setZIndexOffset(100);
            }

            marker.addTo(this.leafletMap);
            marker.addEventListener("click", () => {
                this.props.setSelectedLocation(loc.id);
            });
            const markerTooltipText =
                "<b>" + loc.name + "</b><br>" + loc.street + "<br>" + loc.zip_code + " " + loc.city;
            marker.bindTooltip(markerTooltipText, { direction: "bottom", permanent: "true" });

            this.markers.push(marker);
        }
    },
});
