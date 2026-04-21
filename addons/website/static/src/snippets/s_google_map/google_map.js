/* global google */

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class GoogleMap extends Interaction {
    static selector = ".s_google_map";
    dynamicContent = {
        _window: {
            "t-on-resize": () => {
                if (this.gps) {
                    this.map.setCenter(this.gps);
                }
            },
        },
    };

    setup() {
        this.canStart = false;
        this.canSpecifyKey = false;
        this.map = undefined;
        this.gps = undefined;
    }

    async willStart() {
        if (typeof google !== "object" || typeof google.maps !== "object") {
            // @TODO mysterious-egg: this would not be needed if we didn't
            // duplicate the API loading:
            const refetch = window.top.refetchGoogleMaps;
            window.top.refetchGoogleMaps = false;
            const key = await this.services.google_maps.loadGMapsAPI(this.canSpecifyKey, refetch);
            if (!key) {
                return;
            }
        }
        await google.maps.importLibrary("maps");
        await google.maps.importLibrary("marker");
        this.canStart = true;
    }

    start() {
        if (!this.canStart) {
            return;
        }
        // Default options, will be overwritten by the user
        const myOptions = {
            zoom: 12,
            center: new google.maps.LatLng(50.854975, 4.3753899),
            mapTypeId: google.maps.MapTypeId.ROADMAP,
            panControl: false,
            zoomControl: false,
            mapTypeControl: false,
            streetViewControl: false,
            scrollwheel: false,
            mapId: this.el.dataset.mapId || "DEMO_MAP_ID",
        };

        // Render Map
        const mapC = this.el.querySelector(".map_container");
        const map = new google.maps.Map(mapC, myOptions);

        // Update GPS position
        const p = this.el.dataset.mapGps.substring(1).slice(0, -1).split(",");

        this.gps = new google.maps.LatLng(p[0], p[1]);
        map.setCenter(this.gps);

        // Create Marker & Infowindow
        const markerOptions = {
            map: map,
            position: new google.maps.LatLng(p[0], p[1]),
        };
        if (this.el.dataset.pinStyle === "flat") {
            const iconImgEl = document.createElement("img");
            iconImgEl.src = "/website/static/src/img/snippets_thumbs/s_google_map_marker.png";
            iconImgEl.alt = _t("Map Marker");
            markerOptions.content = iconImgEl;
        }
        new google.maps.marker.AdvancedMarkerElement(markerOptions);

        map.setMapTypeId(google.maps.MapTypeId[this.el.dataset.mapType]); // Update Map Type
        map.setZoom(parseInt(this.el.dataset.mapZoom)); // Update Map Zoom

        this.map = map;
    }
}

registry.category("public.interactions").add("website.google_map", GoogleMap);
