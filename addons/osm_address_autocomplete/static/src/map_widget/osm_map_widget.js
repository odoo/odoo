import { useState, useEffect, useRef } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class OSMMapWidget {
    static template = "osm_address_autocomplete.OSMMapTemplate";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.mapContainer = useRef("mapContainer");
        this.map = null;
        this.marker = null;

        useEffect(
            () => {
                this.initializeMap();
            },
            () => []
        );

        useEffect(
            () => {
                this.updateMapMarker();
            },
            () => [
                this.props.record.data.latitude,
                this.props.record.data.longitude,
            ]
        );
    }

    initializeMap() {
        if (!this.mapContainer.el || !window.L || this.map) {
            return;
        }

        // Coordinadas por defecto (centro de España)
        const defaultLat = this.props.record.data.latitude || 40.4637;
        const defaultLon = this.props.record.data.longitude || -3.7492;
        const defaultZoom = this.props.record.data.latitude ? 15 : 6;

        this.map = window.L.map(this.mapContainer.el).setView(
            [defaultLat, defaultLon],
            defaultZoom
        );

        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19,
        }).addTo(this.map);

        // Agregar marcador si hay coordenadas
        if (this.props.record.data.latitude && this.props.record.data.longitude) {
            this.addMarker(
                this.props.record.data.latitude,
                this.props.record.data.longitude
            );
        }
    }

    updateMapMarker() {
        if (!this.map) {
            return;
        }

        const lat = this.props.record.data.latitude;
        const lon = this.props.record.data.longitude;

        if (lat && lon && typeof lat === "number" && typeof lon === "number") {
            this.addMarker(lat, lon);
            this.map.setView([lat, lon], 15);
        }
    }

    addMarker(lat, lon) {
        // Remover marcador anterior
        if (this.marker) {
            this.map.removeLayer(this.marker);
        }

        // Agregar nuevo marcador
        this.marker = window.L.marker([lat, lon]).addTo(this.map);
        this.marker.bindPopup(`
            <div>
                <strong>Ubicación:</strong><br/>
                Lat: ${lat.toFixed(6)}<br/>
                Lon: ${lon.toFixed(6)}
            </div>
        `).openPopup();
    }
}

