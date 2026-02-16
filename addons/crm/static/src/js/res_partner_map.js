odoo.define('crm.PartnerMap', function (require) {
    'use strict';

    const FormController = require('web.FormController');
    const rpc = require('web.rpc');

    FormController.include({
        _onLoadRecord: function (record) {
            const result = this._super.apply(this, arguments);
            
            if (this.modelName === 'res.partner') {
                setTimeout(() => {
                    this._initializePartnerMap();
                }, 100);
            }
            
            return result;
        },

        _initializePartnerMap: function () {
            const mapContainer = document.getElementById('map-partner-container');
            if (!mapContainer) {
                return;
            }

            // Esperar a que Leaflet esté disponible
            const checkLeaflet = setInterval(() => {
                if (typeof L !== 'undefined') {
                    clearInterval(checkLeaflet);
                    this._renderPartnerMap();
                }
            }, 100);

            // Timeout de seguridad (5 segundos)
            setTimeout(() => {
                clearInterval(checkLeaflet);
            }, 5000);
        },

        _renderPartnerMap: function () {
            const mapContainer = document.getElementById('map-partner-container');
            if (!mapContainer) {
                return;
            }

            // Obtener datos del formulario actual
            const record = this.model.get(this.dataPointID);
            if (!record) {
                return;
            }

            const partner = record.data;
            const street = partner.street || '';
            const city = partner.city || '';
            const state = partner.state_id ? (Array.isArray(partner.state_id) ? partner.state_id[1] : partner.state_id) : '';
            const country = partner.country_id ? (Array.isArray(partner.country_id) ? partner.country_id[1] : partner.country_id) : 'España';
            const zip = partner.zip || '';

            const fullAddress = [street, zip, city, state, country].filter(Boolean).join(', ');

            // Limpiar el contenedor
            mapContainer.innerHTML = '';

            // Crear el mapa
            let map;
            try {
                map = L.map(mapContainer).setView([40.4637, -3.7492], 13); // Centro en Madrid por defecto
            } catch (e) {
                console.log('Error inicializando mapa:', e);
                mapContainer.innerHTML = '<p style="color: #999; padding: 20px;">No se pudo cargar el mapa</p>';
                return;
            }

            // Agregar capa de azulejos
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19,
            }).addTo(map);

            // Si hay dirección, geocodificar
            if (fullAddress && fullAddress.length > 5) {
                this._geocodeAddress(fullAddress, map);
            } else {
                mapContainer.innerHTML += '<p style="color: #999; padding: 10px; font-size: 12px;">Dirección incompleta para geocodificar</p>';
            }
        },

        _geocodeAddress: function (address, map) {
            const mapContainer = document.getElementById('map-partner-container');
            if (!mapContainer) {
                return;
            }

            // Usar Nominatim para geocodificar
            fetch('https://nominatim.openstreetmap.org/search?format=json&limit=1&q=' + encodeURIComponent(address), {
                headers: {
                    'User-Agent': 'Odoo-Partner-Map/1.0'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    const result = data[0];
                    const lat = parseFloat(result.lat);
                    const lon = parseFloat(result.lon);

                    // Centrar el mapa en la ubicación encontrada
                    map.setView([lat, lon], 15);

                    // Agregar marcador
                    const marker = L.marker([lat, lon]).addTo(map);
                    marker.bindPopup(`
                        <div style="font-size: 12px;">
                            <strong>${address}</strong><br/>
                            <small>Lat: ${lat.toFixed(6)}<br/>Lon: ${lon.toFixed(6)}</small>
                        </div>
                    `).openPopup();
                } else {
                    console.log('Dirección no encontrada:', address);
                }
            })
            .catch(error => {
                console.log('Error geocodificando:', error);
            });
        },
    });
});
