import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class AddressMap extends Component {
    static template = "base_address_extended.AddressMap";
    static props = {
        address: { type: String, optional: true },
        latitude: { type: Number, optional: true },
        longitude: { type: Number, optional: true },
        zoom: { type: Number, optional: true, default: 15 },
        widgetId: { type: String, optional: true, default: "map" },
    };

    setup() {
        this.state = useState({
            loading: false,
            error: null,
        });
        
        onMounted(() => {
            this.initMap();
        });
    }

    async initMap() {
        const { latitude, longitude, address, zoom, widgetId } = this.props;
        
        // Inyectar Leaflet dinámicamente si no existe
        if (!window.L) {
            await this.loadLeaflet();
        }

        const mapElement = document.getElementById(`map-container-${widgetId}`);
        if (!mapElement) {
            console.warn(`Map element with id 'map-container-${widgetId}' not found`);
            return;
        }

        // Crear mapa
        const map = window.L.map(mapElement).setView([51.505, -0.09], zoom);

        // Agregar tiles de OpenStreetMap
        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19,
            minZoom: 1,
        }).addTo(map);

        // Si tienes coordenadas exactas
        if (latitude && longitude && (latitude !== 0 || longitude !== 0)) {
            this.addMarker(map, latitude, longitude, address || "Ubicación");
            map.setView([latitude, longitude], zoom);
        } else if (address) {
            // Geocodificar la dirección
            this.state.loading = true;
            await this.geocodeAddress(address, map, zoom);
            this.state.loading = false;
        }
    }

    addMarker(map, lat, lng, title) {
        const marker = window.L.marker([lat, lng]).addTo(map);
        if (title) {
            marker.bindPopup(`<div style="padding: 8px;"><strong>${title}</strong></div>`);
            marker.openPopup();
        }
        return marker;
    }

    async geocodeAddress(address, map, zoom) {
        try {
            const encodedAddress = encodeURIComponent(address);
            const response = await fetch(
                `https://nominatim.openstreetmap.org/search?format=json&q=${encodedAddress}&limit=1`,
                {
                    headers: {
                        'User-Agent': 'Odoo-Partner-Map/1.0'
                    }
                }
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            
            if (data && data.length > 0) {
                const { lat, lon, display_name } = data[0];
                this.addMarker(map, lat, lon, display_name);
                map.setView([lat, lon], zoom);
                console.log(`Geocoded: ${address} -> ${lat}, ${lon}`);
            } else {
                this.state.error = `No se encontró dirección: ${address}`;
                console.warn(`Could not geocode: ${address}`);
            }
        } catch (error) {
            this.state.error = `Error al geocodificar: ${error.message}`;
            console.error("Geocoding error:", error);
        }
    }

    async loadLeaflet() {
        return new Promise((resolve, reject) => {
            // Cargar CSS de Leaflet
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css";
            link.onload = () => console.log("Leaflet CSS loaded");
            link.onerror = reject;
            document.head.appendChild(link);

            // Cargar JS de Leaflet
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js";
            script.onload = () => {
                console.log("Leaflet JS loaded");
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
}
