/* global google */

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

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

    // mapColors = {
    //     // prettier-ignore
    //     lightMonoMap: [{ "featureType": "administrative.locality", "elementType": "all", "stylers": [{ "hue": "#2c2e33" }, { "saturation": 7 }, { "lightness": 19 }, { "visibility": "on" }] }, { "featureType": "landscape", "elementType": "all", "stylers": [{ "hue": "#ffffff" }, { "saturation": -100 }, { "lightness": 100 }, { "visibility": "simplified" }] }, { "featureType": "poi", "elementType": "all", "stylers": [{ "hue": "#ffffff" }, { "saturation": -100 }, { "lightness": 100 }, { "visibility": "off" }] }, { "featureType": "road", "elementType": "geometry", "stylers": [{ "hue": "#bbc0c4" }, { "saturation": -93 }, { "lightness": 31 }, { "visibility": "simplified" }] }, { "featureType": "road", "elementType": "labels", "stylers": [{ "hue": "#bbc0c4" }, { "saturation": -93 }, { "lightness": 31 }, { "visibility": "on" }] }, { "featureType": "road.arterial", "elementType": "labels", "stylers": [{ "hue": "#bbc0c4" }, { "saturation": -93 }, { "lightness": -2 }, { "visibility": "simplified" }] }, { "featureType": "road.local", "elementType": "geometry", "stylers": [{ "hue": "#e9ebed" }, { "saturation": -90 }, { "lightness": -8 }, { "visibility": "simplified" }] }, { "featureType": "transit", "elementType": "all", "stylers": [{ "hue": "#e9ebed" }, { "saturation": 10 }, { "lightness": 69 }, { "visibility": "on" }] }, { "featureType": "water", "elementType": "all", "stylers": [{ "hue": "#e9ebed" }, { "saturation": -78 }, { "lightness": 67 }, { "visibility": "simplified" }] }],
    //     // prettier-ignore
    //     lillaMap: [{ elementType: "labels", stylers: [{ saturation: -20 }] }, { featureType: "poi", elementType: "labels", stylers: [{ visibility: "off" }] }, { featureType: 'road.highway', elementType: 'labels', stylers: [{ visibility: "off" }] }, { featureType: "road.local", elementType: "labels.icon", stylers: [{ visibility: "off" }] }, { featureType: "road.arterial", elementType: "labels.icon", stylers: [{ visibility: "off" }] }, { featureType: "road", elementType: "geometry.stroke", stylers: [{ visibility: "off" }] }, { featureType: "transit", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "poi", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "poi.government", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "poi.sport_complex", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "poi.attraction", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "poi.business", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "transit", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "transit.station", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "landscape", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "road", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "road.highway", elementType: "geometry.fill", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }, { featureType: "water", elementType: "geometry", stylers: [{ hue: '#2d313f' }, { visibility: "on" }, { lightness: 5 }, { saturation: -20 }] }],
    //     // prettier-ignore
    //     blueMap: [{ stylers: [{ hue: "#00ffe6" }, { saturation: -20 }] }, { featureType: "road", elementType: "geometry", stylers: [{ lightness: 100 }, { visibility: "simplified" }] }, { featureType: "road", elementType: "labels", stylers: [{ visibility: "off" }] }],
    //     // prettier-ignore
    //     retroMap: [{ "featureType": "administrative", "elementType": "all", "stylers": [{ "visibility": "on" }, { "lightness": 33 }] }, { "featureType": "landscape", "elementType": "all", "stylers": [{ "color": "#f2e5d4" }] }, { "featureType": "poi.park", "elementType": "geometry", "stylers": [{ "color": "#c5dac6" }] }, { "featureType": "poi.park", "elementType": "labels", "stylers": [{ "visibility": "on" }, { "lightness": 20 }] }, { "featureType": "road", "elementType": "all", "stylers": [{ "lightness": 20 }] }, { "featureType": "road.highway", "elementType": "geometry", "stylers": [{ "color": "#c5c6c6" }] }, { "featureType": "road.arterial", "elementType": "geometry", "stylers": [{ "color": "#e4d7c6" }] }, { "featureType": "road.local", "elementType": "geometry", "stylers": [{ "color": "#fbfaf7" }] }, { "featureType": "water", "elementType": "all", "stylers": [{ "visibility": "on" }, { "color": "#acbcc9" }] }],
    //     // prettier-ignore
    //     flatMap: [{ "stylers": [{ "visibility": "off" }] }, { "featureType": "road", "stylers": [{ "visibility": "on" }, { "color": "#ffffff" }] }, { "featureType": "road.arterial", "stylers": [{ "visibility": "on" }, { "color": "#fee379" }] }, { "featureType": "road.highway", "stylers": [{ "visibility": "on" }, { "color": "#fee379" }] }, { "featureType": "landscape", "stylers": [{ "visibility": "on" }, { "color": "#f3f4f4" }] }, { "featureType": "water", "stylers": [{ "visibility": "on" }, { "color": "#7fc8ed" }] }, {}, { "featureType": "road", "elementType": "labels", "stylers": [{ "visibility": "on" }] }, { "featureType": "poi.park", "elementType": "geometry.fill", "stylers": [{ "visibility": "on" }, { "color": "#83cead" }] }, { "elementType": "labels", "stylers": [{ "visibility": "on" }] }, { "featureType": "landscape.man_made", "elementType": "geometry", "stylers": [{ "weight": 0.9 }, { "visibility": "off" }] }],
    //     // prettier-ignore
    //     cobaltMap: [{ "featureType": "all", "elementType": "all", "stylers": [{ "invert_lightness": true }, { "saturation": 10 }, { "lightness": 30 }, { "gamma": 0.5 }, { "hue": "#435158" }] }],
    //     // prettier-ignore
    //     cupertinoMap: [{ "featureType": "water", "elementType": "geometry", "stylers": [{ "color": "#a2daf2" }] }, { "featureType": "landscape.man_made", "elementType": "geometry", "stylers": [{ "color": "#f7f1df" }] }, { "featureType": "landscape.natural", "elementType": "geometry", "stylers": [{ "color": "#d0e3b4" }] }, { "featureType": "landscape.natural.terrain", "elementType": "geometry", "stylers": [{ "visibility": "off" }] }, { "featureType": "poi.park", "elementType": "geometry", "stylers": [{ "color": "#bde6ab" }] }, { "featureType": "poi", "elementType": "labels", "stylers": [{ "visibility": "off" }] }, { "featureType": "poi.medical", "elementType": "geometry", "stylers": [{ "color": "#fbd3da" }] }, { "featureType": "poi.business", "stylers": [{ "visibility": "off" }] }, { "featureType": "road", "elementType": "geometry.stroke", "stylers": [{ "visibility": "off" }] }, { "featureType": "road", "elementType": "labels", "stylers": [{ "visibility": "off" }] }, { "featureType": "road.highway", "elementType": "geometry.fill", "stylers": [{ "color": "#ffe15f" }] }, { "featureType": "road.highway", "elementType": "geometry.stroke", "stylers": [{ "color": "#efd151" }] }, { "featureType": "road.arterial", "elementType": "geometry.fill", "stylers": [{ "color": "#ffffff" }] }, { "featureType": "road.local", "elementType": "geometry.fill", "stylers": [{ "color": "black" }] }, { "featureType": "transit.station.airport", "elementType": "geometry.fill", "stylers": [{ "color": "#cfb2db" }] }],
    //     // prettier-ignore
    //     carMap: [{ "featureType": "administrative", "stylers": [{ "visibility": "off" }] }, { "featureType": "poi", "stylers": [{ "visibility": "simplified" }] }, { "featureType": "road", "stylers": [{ "visibility": "simplified" }] }, { "featureType": "water", "stylers": [{ "visibility": "simplified" }] }, { "featureType": "transit", "stylers": [{ "visibility": "simplified" }] }, { "featureType": "landscape", "stylers": [{ "visibility": "simplified" }] }, { "featureType": "road.highway", "stylers": [{ "visibility": "off" }] }, { "featureType": "road.local", "stylers": [{ "visibility": "on" }] }, { "featureType": "road.highway", "elementType": "geometry", "stylers": [{ "visibility": "on" }] }, { "featureType": "water", "stylers": [{ "color": "#84afa3" }, { "lightness": 52 }] }, { "stylers": [{ "saturation": -77 }] }, { "featureType": "road" }],
    //     // prettier-ignore
    //     bwMap: [{ stylers: [{ hue: "#00ffe6" }, { saturation: -100 }] }, { featureType: "road", elementType: "geometry", stylers: [{ lightness: 100 }, { visibility: "simplified" }] }, { featureType: "road", elementType: "labels", stylers: [{ visibility: "off" }] }],
    // };

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
            await this.services.website_map.loadGMapAPI(this.canSpecifyKey, refetch);
            return;
        }
        this.canStart = true;
    }

    async start() {
        if (!this.canStart) {
            return;
        }
        // Define a default map's colors set
        const p = this.el.dataset.mapGps.substring(1).slice(0, -1).split(",");
        this.gps = { lat: Number(p[0]), lng: Number(p[1]) };

        // Default options, will be overwritten by the user
        const myOptions = {
            zoom: 12,
            center: this.gps,
            mapId: "DEMO_MAP_ID",
            mapTypeId: "roadmap",
            panControl: false,
            zoomControl: false,
            mapTypeControl: false,
            streetViewControl: false,
            scrollwheel: false,
            mapTypeControlOptions: {
                mapTypeIds: ["roadmap", "map_style"],
            },
        };

        // Render Map
        const mapC = this.el.querySelector(".map_container");
        const [{ Map }, { AdvancedMarkerElement }] = await Promise.all([
            google.maps.importLibrary("maps"),
            google.maps.importLibrary("marker"),
        ]);
        const map = new Map(mapC, myOptions);

        map.setCenter(this.gps);

        let markerIcon;
        if (this.el.dataset.pinStyle === "flat") {
            markerIcon = document.createElement("img");
            markerIcon.src = "/website/static/src/img/snippets_thumbs/s_google_map_marker.png";
            // Handle the drop animation of the marker
            const intersectionObserver = new IntersectionObserver((entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("s_google_map_drop");
                        intersectionObserver.unobserve(entry.target);
                    }
                }
            });
            intersectionObserver.observe(markerIcon);
            markerIcon.style.opacity = "0";
            markerIcon.addEventListener(
                "animationend",
                () => {
                    markerIcon.classList.remove("s_google_map_drop");
                    markerIcon.style.opacity = "1";
                },
                { once: true }
            );
        } else {
            const { PinElement } = await google.maps.importLibrary("marker");
            markerIcon = new PinElement();
        }

        // Create Marker & Infowindow
        const markerOptions = {
            map,
            position: { lat: Number(p[0]), lng: Number(p[1]) },
            content: markerIcon,
        };

        new AdvancedMarkerElement(markerOptions);

        // Other option to keep the drop animation on both pin (default and flat)
        // google.maps.event.addListenerOnce(map, "idle", () => {
        //     markerIcon.style.opacity = "0";
        //     markerIcon.classList.add("s_google_map_drop");
        //     new AdvancedMarkerElement(markerOptions);
        //     setTimeout(() => {
        //         markerIcon.classList.remove("s_google_map_drop");
        //         markerIcon.style.opacity = "1";
        //     }, 800);
        // });

        map.setMapTypeId(google.maps.MapTypeId[this.el.dataset.mapType]); // Update Map Type
        map.setZoom(parseInt(this.el.dataset.mapZoom)); // Update Map Zoom

        // Update Map Color
        // const mapColorAttr = this.el.dataset.mapColor;
        // if (mapColorAttr) {
        //     const mapColor = this.mapColors[mapColorAttr];
        //     map.mapTypes.set(
        //         "map_style",
        //         new google.maps.StyledMapType(mapColor, { name: "Styled Map" })
        //     );
        //     map.setMapTypeId("map_style");
        // }
        this.map = map;
    }
}

registry.category("public.interactions").add("website.google_map", GoogleMap);
