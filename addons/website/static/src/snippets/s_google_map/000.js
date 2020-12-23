odoo.define('website.s_google_map', function (require) {
'use strict';

const publicWidget = require('web.public.widget');

publicWidget.registry.GoogleMap = publicWidget.Widget.extend({
    selector: '.s_google_map',
    disabledInEditableMode: false,

    mapColors: {
        lightMonoMap: [{"featureType": "administrative.locality", "elementType": "all", "stylers": [{"hue": "#2c2e33"}, {"saturation": 7}, {"lightness": 19}, {"visibility": "on"}]}, {"featureType": "landscape", "elementType": "all", "stylers": [{"hue": "#ffffff"}, {"saturation": -100}, {"lightness": 100}, {"visibility": "simplified"}]}, {"featureType": "poi", "elementType": "all", "stylers": [{"hue": "#ffffff"}, {"saturation": -100}, {"lightness": 100}, {"visibility": "off"}]}, {"featureType": "road", "elementType": "geometry", "stylers": [{"hue": "#bbc0c4"}, {"saturation": -93}, {"lightness": 31}, {"visibility": "simplified"}]}, {"featureType": "road", "elementType": "labels", "stylers": [{"hue": "#bbc0c4"}, {"saturation": -93}, {"lightness": 31}, {"visibility": "on"}]}, {"featureType": "road.arterial", "elementType": "labels", "stylers": [{"hue": "#bbc0c4"}, {"saturation": -93}, {"lightness": -2}, {"visibility": "simplified"}]}, {"featureType": "road.local", "elementType": "geometry", "stylers": [{"hue": "#e9ebed"}, {"saturation": -90}, {"lightness": -8}, {"visibility": "simplified"}]}, {"featureType": "transit", "elementType": "all", "stylers": [{"hue": "#e9ebed"}, {"saturation": 10}, {"lightness": 69}, {"visibility": "on"}]}, {"featureType": "water", "elementType": "all", "stylers": [{"hue": "#e9ebed"}, {"saturation": -78}, {"lightness": 67}, {"visibility": "simplified"}]}],
        lillaMap: [{elementType: "labels", stylers: [{saturation: -20}]}, {featureType: "poi", elementType: "labels", stylers: [{visibility: "off"}]}, {featureType: 'road.highway', elementType: 'labels', stylers: [{visibility: "off"}]}, {featureType: "road.local", elementType: "labels.icon", stylers: [{visibility: "off"}]}, {featureType: "road.arterial", elementType: "labels.icon", stylers: [{visibility: "off"}]}, {featureType: "road", elementType: "geometry.stroke", stylers: [{visibility: "off"}]}, {featureType: "transit", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "poi", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "poi.government", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "poi.sport_complex", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "poi.attraction", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "poi.business", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "transit", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "transit.station", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "landscape", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "road", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "road.highway", elementType: "geometry.fill", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}, {featureType: "water", elementType: "geometry", stylers: [{hue: '#2d313f'}, {visibility: "on"}, {lightness: 5}, {saturation: -20}]}],
        blueMap: [{stylers: [{hue: "#00ffe6"}, {saturation: -20}]}, {featureType: "road", elementType: "geometry", stylers: [{lightness: 100}, {visibility: "simplified"}]}, {featureType: "road", elementType: "labels", stylers: [{visibility: "off"}]}],
        retroMap: [{"featureType": "administrative", "elementType": "all", "stylers": [{"visibility": "on"}, {"lightness": 33}]}, {"featureType": "landscape", "elementType": "all", "stylers": [{"color": "#f2e5d4"}]}, {"featureType": "poi.park", "elementType": "geometry", "stylers": [{"color": "#c5dac6"}]}, {"featureType": "poi.park", "elementType": "labels", "stylers": [{"visibility": "on"}, {"lightness": 20}]}, {"featureType": "road", "elementType": "all", "stylers": [{"lightness": 20}]}, {"featureType": "road.highway", "elementType": "geometry", "stylers": [{"color": "#c5c6c6"}]}, {"featureType": "road.arterial", "elementType": "geometry", "stylers": [{"color": "#e4d7c6"}]}, {"featureType": "road.local", "elementType": "geometry", "stylers": [{"color": "#fbfaf7"}]}, {"featureType": "water", "elementType": "all", "stylers": [{"visibility": "on"}, {"color": "#acbcc9"}]}],
        flatMap: [{"stylers": [{"visibility": "off"}]}, {"featureType": "road", "stylers": [{"visibility": "on"}, {"color": "#ffffff"}]}, {"featureType": "road.arterial", "stylers": [{"visibility": "on"}, {"color": "#fee379"}]}, {"featureType": "road.highway", "stylers": [{"visibility": "on"}, {"color": "#fee379"}]}, {"featureType": "landscape", "stylers": [{"visibility": "on"}, {"color": "#f3f4f4"}]}, {"featureType": "water", "stylers": [{"visibility": "on"}, {"color": "#7fc8ed"}]}, {}, {"featureType": "road", "elementType": "labels", "stylers": [{"visibility": "on"}]}, {"featureType": "poi.park", "elementType": "geometry.fill", "stylers": [{"visibility": "on"}, {"color": "#83cead"}]}, {"elementType": "labels", "stylers": [{"visibility": "on"}]}, {"featureType": "landscape.man_made", "elementType": "geometry", "stylers": [{"weight": 0.9}, {"visibility": "off"}]}],
        cobaltMap: [{"featureType": "all", "elementType": "all", "stylers": [{"invert_lightness": true}, {"saturation": 10}, {"lightness": 30}, {"gamma": 0.5}, {"hue": "#435158"}]}],
        cupertinoMap: [{"featureType": "water", "elementType": "geometry", "stylers": [{"color": "#a2daf2"}]}, {"featureType": "landscape.man_made", "elementType": "geometry", "stylers": [{"color": "#f7f1df"}]}, {"featureType": "landscape.natural", "elementType": "geometry", "stylers": [{"color": "#d0e3b4"}]}, {"featureType": "landscape.natural.terrain", "elementType": "geometry", "stylers": [{"visibility": "off"}]}, {"featureType": "poi.park", "elementType": "geometry", "stylers": [{"color": "#bde6ab"}]}, {"featureType": "poi", "elementType": "labels", "stylers": [{"visibility": "off"}]}, {"featureType": "poi.medical", "elementType": "geometry", "stylers": [{"color": "#fbd3da"}]}, {"featureType": "poi.business", "stylers": [{"visibility": "off"}]}, {"featureType": "road", "elementType": "geometry.stroke", "stylers": [{"visibility": "off"}]}, {"featureType": "road", "elementType": "labels", "stylers": [{"visibility": "off"}]}, {"featureType": "road.highway", "elementType": "geometry.fill", "stylers": [{"color": "#ffe15f"}]}, {"featureType": "road.highway", "elementType": "geometry.stroke", "stylers": [{"color": "#efd151"}]}, {"featureType": "road.arterial", "elementType": "geometry.fill", "stylers": [{"color": "#ffffff"}]}, {"featureType": "road.local", "elementType": "geometry.fill", "stylers": [{"color": "black"}]}, {"featureType": "transit.station.airport", "elementType": "geometry.fill", "stylers": [{"color": "#cfb2db"}]}],
        carMap: [{"featureType": "administrative", "stylers": [{"visibility": "off"}]}, {"featureType": "poi", "stylers": [{"visibility": "simplified"}]}, {"featureType": "road", "stylers": [{"visibility": "simplified"}]}, {"featureType": "water", "stylers": [{"visibility": "simplified"}]}, {"featureType": "transit", "stylers": [{"visibility": "simplified"}]}, {"featureType": "landscape", "stylers": [{"visibility": "simplified"}]}, {"featureType": "road.highway", "stylers": [{"visibility": "off"}]}, {"featureType": "road.local", "stylers": [{"visibility": "on"}]}, {"featureType": "road.highway", "elementType": "geometry", "stylers": [{"visibility": "on"}]}, {"featureType": "water", "stylers": [{"color": "#84afa3"}, {"lightness": 52}]}, {"stylers": [{"saturation": -77}]}, {"featureType": "road"}],
        bwMap: [{stylers: [{hue: "#00ffe6"}, {saturation: -100}]}, {featureType: "road", elementType: "geometry", stylers: [{lightness: 100}, {visibility: "simplified"}]}, {featureType: "road", elementType: "labels", stylers: [{visibility: "off"}]}],
    },

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        if (typeof google !== 'object' || typeof google.maps !== 'object') {
            await new Promise(resolve => {
                this.trigger_up('gmap_api_request', {
                    editableMode: this.editableMode,
                    onSuccess: () => resolve(),
                });
            });
            // The animation will be restarted for all maps as soon as the
            // google map script has been executed.
            return;
        }

        // Define a default map's colors set
        const std = [];
        new google.maps.StyledMapType(std, {name: "Std Map"});

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
            mapTypeControlOptions: {
                mapTypeIds: [google.maps.MapTypeId.ROADMAP, 'map_style']
            }
        };

        // Render Map
        const mapC = this.$('.map_container');
        const map = new google.maps.Map(mapC.get(0), myOptions);

        // Update GPS position
        const p = this.el.dataset.mapGps.substring(1).slice(0, -1).split(',');
        const gps = new google.maps.LatLng(p[0], p[1]);
        map.setCenter(gps);

        // Update Map on screen resize
        google.maps.event.addDomListener(window, 'resize', () => {
            map.setCenter(gps);
        });

        // Create Marker & Infowindow
        const markerOptions = {
            map: map,
            animation: google.maps.Animation.DROP,
            position: new google.maps.LatLng(p[0], p[1])
        };
        if (this.el.dataset.pinStyle === 'flat') {
            markerOptions.icon = '/website/static/src/img/snippets_thumbs/s_google_map_marker.png';
        }
        new google.maps.Marker(markerOptions);

        map.setMapTypeId(google.maps.MapTypeId[this.el.dataset.mapType]); // Update Map Type
        map.setZoom(parseInt(this.el.dataset.mapZoom)); // Update Map Zoom

        // Update Map Color
        const mapColorAttr = this.el.dataset.mapColor;
        if (mapColorAttr) {
            const mapColor = this.mapColors[mapColorAttr];
            map.mapTypes.set('map_style', new google.maps.StyledMapType(mapColor, {name: "Styled Map"}));
            map.setMapTypeId('map_style');
        }
    },
});
});
