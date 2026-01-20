/** @odoo-module */
/* global L */

import { Component, onMounted, onWillStart, onWillUnmount, proxy } from "@odoo/owl";
import { AssetsLoadingError, loadCSS, loadJS } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef } from "@web/owl2/utils";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const TILE_ROUTE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export class LocationPicker extends Component {
    static template = "hr.LocationPicker";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        const {
            location_res_id: resId,
            location_latitude: lat,
            location_longitude: lng,
        } = this.props.action.context || {};

        this.mapRef = useRef("map");

        const hasInitialLocation = lat !== 0 || lng !== 0;

        this.resId = resId;
        this.state = proxy({
            locationSearch: "",
            selectedLocation: hasInitialLocation ? { lat, lng } : null,
            geoPermission: "prompt",
            shouldLoadMap: false,
        });

        onWillStart(async () => {
            /**
             * We load the script for the map before rendering the owl component to avoid a
             * UserError if the script can't be loaded (e.g. if the customer loses the connection
             * between the rendering of the page and when he opens the location selector, or if the
             * CDN's doesn't host the library anymore).
             */
            try {
                await Promise.all([
                    loadJS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'),
                    loadCSS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'),
                ]);
                this.state.shouldLoadMap = true;
            } catch (error) {
                if (!(error instanceof AssetsLoadingError)) {
                    throw error;
                }
            }

            try {
                const geoPermission = await browser.navigator.permissions.query({ name: "geolocation" });
                this.state.geoPermission = geoPermission.state;
            } catch {
                this.state.geoPermission = "unsupported";
            }
        });
        onMounted(() => this.setupMap());
        onWillUnmount(() => this.teardownMap());
    }

    setupMap() {
        if (!this.mapRef.el || !this.state.shouldLoadMap) {
            return;
        }

        if (typeof L === 'undefined') {
            this.notification.add(_t("Map library failed to load. Please refresh the page."), { type: "danger" });
            return;
        }

        this.map = L.map(this.mapRef.el);
        L.tileLayer(TILE_ROUTE, {
            maxZoom: 19,
        }).addTo(this.map);

        this.map.on("click", (ev) => this.onMapClick(ev));
        if (this.state.selectedLocation) {
            const { lat, lng } = this.state.selectedLocation;
            this.map.setView([lat, lng], 15);
            this._placeMarker(this.state.selectedLocation);
        } else {
            this.useCurrentLocation();
        }
    }

    teardownMap() {
        if (this.map) {
            this.map.remove();
            this.map = undefined;
        }
        this.marker = undefined;
    }

    /**
     * @param {MouseEvent} ev
     */
    onMapClick(ev) {
        const { lat, lng } = ev.latlng;
        this._selectLocation(lat, lng);
    }

    /**
     * @param {number} lat
     * @param {number} lng
     */
    _selectLocation(lat, lng) {
        this.state.selectedLocation = { lat, lng };
        this._placeMarker(this.state.selectedLocation);
        if (this.map) {
            this.map.setView([lat, lng], 15);
        }
    }

    _placeMarker({ lat, lng }) {
        if (!this.map) {
            return;
        }
        if (this.marker) {
            this.marker.setLatLng([lat, lng]);
        } else {
            this.marker = L.marker([lat, lng]).addTo(this.map);
        }
    }

    async onSearchLocation(ev) {
        ev.preventDefault();
        const query = this.state.locationSearch.trim();
        if (!query) {
            return;
        }

        const result = await this.orm.call("base.geocoder", "geo_find", [query]);
        if (!result || result.length < 2) {
            this.notification.add(_t("No location found for your search."), { type: "warning" });
            return;
        }
        const [lat, lng] = result;
        this._selectLocation(lat, lng);
    }

    useCurrentLocation() {
        if (!navigator.geolocation) {
            this.notification.add(_t("Your browser does not support geolocation."), { type: "warning" });
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                this._selectLocation(lat, lng);
            },
            () => {
                this.notification.add(_t("Unable to retrieve your location."), { type: "danger" });
            }
        );
    }

    async onSaveLocation() {
        if (!this.state.selectedLocation) {
            this.notification.add(
                _t("Please select a location on the map before saving."),
                { type: "warning" }
            );
            return;
        }

        const { lat, lng } = this.state.selectedLocation;

        const payload = {
            latitude: lat,
            longitude: lng,
        };

        try {
            await this.orm.write("hr.work.location", [this.resId], payload);

            this.notification.add(_t("Location saved successfully."), { type: "success" });
            this.actionService.doAction({ type: "ir.actions.act_window_close" });

        } catch (error) {
            let errorMessage;
            if (!navigator.onLine) {
                errorMessage = _t("No internet connection. Please check your network and try again.");
            } else if (error instanceof RPCError && error.exceptionName === "odoo.exceptions.ValidationError") {
                errorMessage = _t("The selected coordinates are not valid. Please choose a different location.");
            } else if (error instanceof RPCError && error.exceptionName === "odoo.exceptions.AccessError") {
                errorMessage = _t("You do not have permission to modify work locations. Please contact your administrator.");
            } else {
                throw error;
            }
            this.notification.add(errorMessage, { type: "danger", sticky: true });
        }
    }

    onDiscardLocation() {
        this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("open_location_map", LocationPicker);
