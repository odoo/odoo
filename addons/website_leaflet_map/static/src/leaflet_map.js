
function initialize_map() {
    //'use strict';

    var map = L.map('odoo-leaflet-map');

    var partner_url = document.body.getAttribute('data-partner-url') || '';

    // TODO make tile server configurable.
    L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
	attribution: '&#169; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    var myIcon = L.icon({
	iconUrl: '/website_leaflet_map/static/src/images/partners.png',
	iconSize: [25, 25],
	iconAnchor: [12, 25],
	popupAnchor: [0, -20]
    });

    var bounds;

    for (var i = 0; i <  odoo_partner_data.partners.length; i++) {
	var p = odoo_partner_data.partners[i];
	var ll = L.latLng(p.latitude, p.longitude);
	if (bounds === undefined) {
	    bounds = L.latLngBounds(ll, ll);
	}
	bounds.extend(ll);
	L.marker([p.latitude, p.longitude], {icon: myIcon}).addTo(map)
	    .bindPopup(
		'<div class="marker">'+
		(partner_url.length ? '<a target="_top" href="'+partner_url+p.id+'"><b>'+p.name +'</b></a>' : '<b>'+p.name+'</b>' )+
		(p.type ? '  <b>' + p.type + '</b>' : '')+
		'  <pre>' + p.address + '</pre>'+
		'</div>'
	    );
    }

    if (bounds == undefined) {
	// worst case: no partner at all, show whole world
	map.fitWorld();
    } else {
	bounds.pad(2);
	map.fitBounds(bounds);
    }
}

document.body.onload=initialize_map();
