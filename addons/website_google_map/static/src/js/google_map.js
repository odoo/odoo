function initialize(pt) {
  var center = new google.maps.LatLng(10.91, 5.38);
  var Geocoder = new google.maps.Geocoder();

  var map = new google.maps.Map(document.getElementById('map'), {
    zoom: 1,
    center: center,
    mapTypeId: google.maps.MapTypeId.ROADMAP
  });

  var infoWindow = new google.maps.InfoWindow();

  google.maps.event.addListener(map, 'click', function() {
     infoWindow.close();
  });

  var partners = new google.maps.MarkerImage("/website_google_map/static/src/img/partners.png",new google.maps.Size(25, 25));

  var markers = [];

  var onMarkerClick = function() {
    var marker = this;
    var p = marker.partner;
    infoWindow.setContent(
          '<div class="marker">'+
          (partner_url.length ? '<a target="_top" href="'+partner_url+p.id+'"><b>'+p.name +'</b></a>' : '<b>'+p.name+'</b>' )+ '<br/>'+
          (p.type ? '  <b>' + p.type + '</b>' : '')+
          '  <pre>' + p.address + '</pre>'+
          '</div>'
      );
    infoWindow.open(map, marker);
  };

  var set_marker = function(partner) {
    if (!partner.latitude && !partner.longitude) {

      Geocoder.geocode( { 'address': partner.address}, function(results, status) {
        if (status == google.maps.GeocoderStatus.OK) {
          var location = results[0].geometry.location;

          $.post("/google_map/set_partner_position/", {
              'partner_id': partner.id,
              'latitude': location.ob,
              'longitude': location.pb
          });
          partner.latitude = location.ob;
          partner.longitude = location.pb;

          map.setCenter(results[0].geometry.location);
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
        position: latLng
      });
      google.maps.event.addListener(marker, 'click', onMarkerClick);
      markers.push(marker);
    }

  };

  if (data)
  for (var i = 0; i < data.counter; i++) {
    set_marker(data.partners[i]);
  }
  var markerCluster = new MarkerClusterer(map, markers);
}
google.maps.event.addDomListener(window, 'load', initialize);

