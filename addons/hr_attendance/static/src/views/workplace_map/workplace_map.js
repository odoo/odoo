/*global L*/

import { Component, useEffect, onWillStart } from "@odoo/owl";
import { AssetsLoadingError, loadCSS, loadJS } from '@web/core/assets';
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class WorkplaceMap extends Component {
    static template = "hr_attendance.WorkplaceMap";
    static props = { ...standardActionServiceProps };
    setup() {
        this.leafletMap = null;
        this.marker = null;
        this.companyAddress = null;
        this.selectedCoords = null;
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.current_company_id = user.activeCompany.id;

        onWillStart(async () => {
            try {
                await Promise.all([
                    loadJS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'),
                    loadJS('https://unpkg.com/leaflet-control-geocoder/dist/Control.Geocoder.js'),
                    loadCSS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'),
                    loadCSS('https://unpkg.com/leaflet-control-geocoder/dist/Control.Geocoder.css'),
                ]);
                this.companyData = await this.orm.searchRead("res.company", [["id", "=", this.current_company_id]], ["workplace_location", "workplace_latitude", "workplace_longitude"])
                this.company = this.companyData[0];
                if (this.company.workplace_location) {
                    this.companyAddress = [this.company.workplace_latitude, this.company.workplace_longitude].join(",");
                    this.selectedCoords = L.latLng(this.company.workplace_latitude, this.company.workplace_longitude);
                }
                else{
                    const geo = await this.getGeoLocation();
                    if (geo.success) {
                        this.companyAddress = [geo.latitude, geo.longitude].join(",");
                        this.selectedCoords = L.latLng(geo.latitude, geo.longitude);
                    } else {
                        this.notification.add(geo.message, { type: "warning" });
                    }
                }
            } catch (error) {
                if (!(error instanceof AssetsLoadingError)) {
                    throw error;
                }
            }
        });

        useEffect(
            () => {
                if (this.companyAddress) {
                    this.fetchAndCenterMap(this.companyAddress);
                }
            }
        );

    }

    async onClose() {
        return this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }

    async getPosition() {
        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
            });
        });
    }

    async getGeoLocation() {
        try {
            const position = await this.getPosition();
            return {
                success: true,
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            };
        } catch (err) {
            return {
                success: false,
                message: _t("Location error: %s", err.message || err),
            };
        }
    }

    async fetchAndCenterMap(companyAddress){
        const geoRes = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(companyAddress)}&format=jsonv2`);
        const geoData = await geoRes.json();

        if (geoData.length > 0) {
            const lat = parseFloat(geoData[0].lat);
            const lon = parseFloat(geoData[0].lon);

            this.leafletMap = L.map("workplace_map").setView([lat, lon], 15);

            L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                attribution: "&copy; <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>"
            }).addTo(this.leafletMap);

            this.marker = L.marker([lat, lon]).addTo(this.leafletMap).bindPopup(geoData[0].display_name).openPopup();
            this.leafletMap.on("click", (e) => {
                if (this.marker) this.leafletMap.removeLayer(this.marker);
                this.marker = L.marker(e.latlng).addTo(this.leafletMap);
                this.selectedCoords = e.latlng;
            });

            if (L.Control && L.Control.Geocoder) {
                L.Control.geocoder({
                    defaultMarkGeocode: false
                })
                .on("markgeocode", (e) => {
                    const latlng = e.geocode.center;
                    if (this.marker) this.leafletMap.removeLayer(this.marker);
                    this.marker = L.marker(latlng).addTo(this.leafletMap);
                    this.selectedCoords = latlng;
                    this.leafletMap.setView(latlng, 15);
                })
                .addTo(this.leafletMap);
            } else {
                this.notification.add(_t("Leaflet Geocoder not loaded"), { type: "danger" });
            }
        } else {
            this.notification.add(_t("Could not fetch coordinates for company address"), { type: "danger" });
        }
    }

    async saveCoords() {
        try {
            await rpc("/web/dataset/call_kw/res.company/write", {
                model: "res.company",
                method: "write",
                args: [[this.current_company_id], {
                    workplace_latitude: this.selectedCoords.lat,
                    workplace_longitude: this.selectedCoords.lng,
                    workplace_location: `${this.selectedCoords.lat.toFixed(5)}, ${this.selectedCoords.lng.toFixed(5)}`,
                }],
                kwargs: {},
            });
        } catch (err) {
            this.notification.add(_t("Failed to save location") + err, { type: "danger" });
        }
    }
}

registry.category("actions").add("open_workplace_location_map", WorkplaceMap);
