Partner geolocalize
===================

Contacts geolocation API to convert partner addresses into GPS coordinates.

Configure
---------
You can add a system parameter to change the default provider of the geolocation API service.

* `base_geolocalize.provider = <service>`

A method `_call_<service>` should be implemented in object `base.geocoder` that accepts an address string as parameter and return (latitude, longitude) tuple for this to work.
If no parameter is set, Openstreetmap will be used by default.

An optional method `_geo_query_address_<service>` which takes address fields as parameters can be defined to encode the query string for the provider.

Google Places
-------------
You can use Google Maps API if you have a valid apikey. In that case you should add the following system parameters:

* `base_geolocalize.provider = google`
* `google.api_key_geocode = <your_api_key>`
