Partner geolocalize
===================

Contacts geolocation API to convert partner addresses into GPS coordinates.

Configure
---------
You can add a system parameter to change the default provider of the geolocation API service.

* `base_geolocalize.provider = <service>`

A method `_call_<service>` should be implemented in object `base.geocoder` that accepts an address string as parameter and return (latitude, longitude) tuple for this to work.
If no parameter is set, Openstreetmap will be used by default.
