function initialize_map() {
    'use strict';

    // MAP CONFIG AND LOADING
    var map = new google.maps.Map(document.getElementById('odoo-google-map'), {
        zoom: 1,
        center: {lat: 0.0, lng: 0.0},
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });

    // ENABLE ADDRESS GEOCODING
    var Geocoder = new google.maps.Geocoder();

    // INFO BUBBLES
    var infoWindow = new google.maps.InfoWindow();
    var partners = new google.maps.MarkerImage('/website_google_map/static/src/img/partners.png', new google.maps.Size(25, 25));
    var partner_url = document.body.getAttribute('data-partner-url') || '';
    var markers = [];
    var options = {
        imagePath: '/website_google_map/static/src/lib/images/m'
    };

    google.maps.event.addListener(map, 'click', function() {
        infoWindow.close();
    });

    // Display the bubble once clicked
    var onMarkerClick = function() {
        var marker = this;
        var p = marker.partner;
        infoWindow.setContent(
              '<div class="marker">'+
              (partner_url.length ? '<a target="_top" href="'+partner_url+p.id+'"><b>'+p.name +'</b></a>' : '<b>'+p.name+'</b>' )+
              (p.type ? '  <b>' + p.type + '</b>' : '')+
              '  <pre>' + p.address + '</pre>'+
              '</div>'
          );
        infoWindow.open(map, marker);
    };

    // Create a bubble for a partner
    var set_marker = function(partner) {
        // If no lat & long, geocode address
        // TODO: a server cronjob that will store these coordinates in database instead of resolving them on-the-fly
        if (!partner.latitude && !partner.longitude) {
            Geocoder.geocode({'address': partner.address}, function(results, status) {
                if (status === google.maps.GeocoderStatus.OK) {
                    var location = results[0].geometry.location;
                    partner.latitude = location.ob;
                    partner.longitude = location.pb;
                    var marker = new google.maps.Marker({
                        partner: partner,
                        map: map,
                        icon: partners,
                        position: location
                    });
                    google.maps.event.addListener(marker, 'click', onMarkerClick);
                    markers.push(marker);
                } else {
                    console.debug('Geocode was not successful for the following reason: ' + status);
                }
            });
        } else {
            var latLng = new google.maps.LatLng(partner.latitude, partner.longitude);
            var marker = new google.maps.Marker({
                partner: partner,
                icon: partners,
                map: map,
                position: latLng
            });
            google.maps.event.addListener(marker, 'click', onMarkerClick);
            markers.push(marker);
        }
    };

    // Create the markers and cluster them on the map
    if (odoo_partner_data){ /* odoo_partner_data special variable should have been defined in google_map.xml */
        for (var i = 0; i < odoo_partner_data.counter; i++) {
            set_marker(odoo_partner_data.partners[i]);
        }
        var markerCluster = new MarkerClusterer(map, markers, options);
    }
}

// Initialize map once the DOM has been loaded
google.maps.event.addDomListener(window, 'load', initialize_map);
