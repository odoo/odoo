odoo.define('base_address_extended.partner_map', function(require) {
    'use strict';

    const FormController = require('web.FormController');

    FormController.include({
        _update: function(state) {
            const result = this._super.apply(this, arguments);
            if (this.modelName === 'res.partner') {
                this._loadAndRenderMap();
            }
            return result;
        },

        start: function() {
            const result = this._super.apply(this, arguments);
            if (this.modelName === 'res.partner') {
                setTimeout(() => {
                    this._loadAndRenderMap();
                }, 500);
            }
            return result;
        },

        _loadAndRenderMap: function() {
            try {
                const state = this.model.get(this.handle);
                if (!state || !state.data) {
                    return;
                }

                const latitude = state.data.partner_latitude || 0;
                const longitude = state.data.partner_longitude || 0;
                const name = state.data.name || '';
                const street = state.data.street || '';
                const city = state.data.city || '';

                const container = document.getElementById('map-partner-container');
                if (!container) {
                    return;
                }

                // Cargar Leaflet si no existe
                if (!window.L) {
                    this._loadLeafletLibrary().then(() => {
                        this._renderMap(container, latitude, longitude, name, street, city);
                    });
                } else {
                    this._renderMap(container, latitude, longitude, name, street, city);
                }
            } catch (error) {
                console.error('Error loading map:', error);
            }
        },

        _renderMap: function(container, latitude, longitude, name, street, city) {
            // Limpiar contenedor
            container.innerHTML = '';

            // Coordenadas por defecto (España)
            let centerLat = 40.46366;
            let centerLng = -3.74922;
            let zoom = 4;

            // Si tenemos coordenadas válidas, usarlas
            if (latitude && longitude && (latitude !== 0 || longitude !== 0)) {
                centerLat = latitude;
                centerLng = longitude;
                zoom = 15;
            }

            try {
                // Crear mapa
                const map = L.map(container, {
                    center: [centerLat, centerLng],
                    zoom: zoom,
                    attributionControl: true,
                }).setView([centerLat, centerLng], zoom);

                // Agregar tiles de OpenStreetMap
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                    maxZoom: 19,
                    minZoom: 1,
                }).addTo(map);

                // Agregar marcador si hay coordenadas
                if (latitude && longitude && (latitude !== 0 || longitude !== 0)) {
                    const popupText = `<div style="padding: 8px; min-width: 200px;">
                        <strong style="display: block; margin-bottom: 5px; font-size: 14px;">${name}</strong>
                        ${street ? `<small style="display: block;">${street}</small>` : ''}
                        ${city ? `<small style="display: block;">${city}</small>` : ''}
                        <small style="display: block; margin-top: 8px; color: #666;">
                            <strong>Lat:</strong> ${latitude.toFixed(6)}<br/>
                            <strong>Lon:</strong> ${longitude.toFixed(6)}
                        </small>
                    </div>`;

                    const marker = L.marker([latitude, longitude]).addTo(map);
                    marker.bindPopup(popupText);
                    marker.openPopup();

                    // Asegurar que el mapa se redibuja correctamente
                    setTimeout(() => {
                        map.invalidateSize();
                    }, 100);
                } else {
                    console.log('Sin coordenadas válidas para el mapa');
                }
            } catch (error) {
                console.error('Error rendering map:', error);
                container.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">Error al cargar el mapa</p>';
            }
        },

        _loadLeafletLibrary: function() {
            return new Promise((resolve, reject) => {
                // Cargar CSS
                const cssLink = document.createElement('link');
                cssLink.rel = 'stylesheet';
                cssLink.href = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
                cssLink.integrity = 'sha512-XwwWDnDdsLXd7VWghqlAwZBHnlz7B1yUqVEL/t0x0x0YHn2dRd8wMOQGb6H8VCnA6V8XPNKhVMoQ8a4cA1q0xA==';
                cssLink.crossOrigin = 'anonymous';
                document.head.appendChild(cssLink);

                // Cargar JS
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
                script.integrity = 'sha512-WXoSL2lrKOSIDHgcnQlJ76jpo3aAkkas63CEQEQc+NgPORc41ckbMjsTTkAtn2XVميOvQIc+RTka50PrkgjwQ==';
                script.crossOrigin = 'anonymous';
                script.onload = () => {
                    console.log('Leaflet library loaded');
                    resolve();
                };
                script.onerror = () => {
                    console.error('Failed to load Leaflet');
                    reject(new Error('Failed to load Leaflet'));
                };
                document.head.appendChild(script);
            });
        }
    });
});

