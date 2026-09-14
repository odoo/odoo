import logging

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class GeocoderProvider(models.Model):
    """Configured geolocation provider (technical name + label) selectable in settings."""

    _name = "geocoder.provider"
    _description = "Geocoding Provider"

    tech_name = fields.Char(string="Technical Name")
    name = fields.Char()


class Geocoder(models.AbstractModel):
    """Call a geocoding API and convert addresses into GPS coordinates."""

    _name = "geocoder"
    _description = "Geocoder"

    @api.model
    def _get_provider(self):
        prov_id = (
            self.env["ir.config_parameter"].sudo().get_param("geocoding.geo_provider")
        )
        provider = self.env["geocoder.provider"]
        if prov_id:
            try:
                provider = self.env["geocoder.provider"].browse(int(prov_id))
            except ValueError:
                provider = self.env["geocoder.provider"]
        if not prov_id or not provider.exists():
            provider = self.env["geocoder.provider"].search([], limit=1)
        return provider

    @api.model
    def geo_query_address(
        self, street=None, zip_code=None, city=None, state=None, country=None
    ):
        """Converts address fields into a valid string for querying
        geolocation APIs.
        :param street: street address
        :param zip_code: zip code
        :param city: city
        :param state: state
        :param country: country
        :return: formatted string
        """
        provider = self._get_provider().tech_name
        if hasattr(self, "_geo_query_address_" + provider):
            return getattr(self, "_geo_query_address_" + provider)(
                street, zip_code, city, state, country
            )
        else:
            # By default, join the non-empty parameters
            return self._geo_query_address_default(
                street=street,
                zip_code=zip_code,
                city=city,
                state=state,
                country=country,
            )

    @api.model
    def geo_find(self, addr, **kw):
        """Use a location provider API to convert an address string into a latitude, longitude tuple.
        Here we use Openstreetmap Nominatim by default.
        :param addr: Address string passed to API
        :return: (latitude, longitude) or None if not found
        """
        provider = self._get_provider().tech_name
        try:
            service = getattr(self, "_call_" + provider)
            result = service(addr, **kw)
        except AttributeError as exc:
            raise UserError(
                _("Provider %s is not implemented for geolocation service.", provider)
            ) from exc
        except UserError:
            raise
        except Exception:
            _logger.debug("Geolocalize call failed", exc_info=True)
            result = None
        return result

    @api.model
    def _call_openstreetmap(self, addr, **kw):
        """
        Use Openstreemap Nominatim service to retrieve location
        :return: (latitude, longitude), or None if addr is empty or the provider found no match
        """
        if not addr:
            _logger.info("invalid address given")
            return None
        url = "https://nominatim.openstreetmap.org/search"
        try:
            headers = {"User-Agent": "Odoo (http://www.odoo.com/contactus)"}
            response = self.env["ir.egress"].request(
                "GET",
                url,
                purpose="geocoding",
                headers=headers,
                params={"format": "json", "q": addr},
                timeout=10,
            )
            _logger.info("openstreetmap nominatim service called")
            if response.status_code != 200:
                _logger.warning(
                    "Request to openstreetmap failed.\nCode: %s\nContent: %s",
                    response.status_code,
                    response.content,
                )
                raise ValueError("Nominatim returned HTTP %s" % response.status_code)
            result = response.json()
        except Exception as e:
            self._raise_query_error(e)
        if not result:
            return None
        geo = result[0]
        return float(geo["lat"]), float(geo["lon"])

    @api.model
    def _call_openstreetmap_reverse(self, lat, lon):
        """
        Use Openstreemap Nominatim service to retrieve location from latitude and longitude
        :param lat: Latitude
        :param lon: Longitude
        :return: parsed JSON response (dict) from the Nominatim reverse endpoint, or None if lat/lon are missing

        """
        if not (lat and lon):
            _logger.info("invalid latitude or longitude given")
            return None
        if tools.config["test_enable"] or modules.module.current_test:
            raise UserError(_("OpenStreetMap calls disabled in testing environment."))
        try:
            headers = {"User-Agent": "Odoo (http://www.odoo.com/contactus)"}
            response = self.env["ir.egress"].request(
                "GET",
                "https://nominatim.openstreetmap.org/reverse",
                purpose="geocoding",
                headers=headers,
                params={"format": "json", "lat": lat, "lon": lon},
                timeout=10,
            )
            _logger.info("openstreetmap nominatim service called")
            if response.status_code != 200:
                _logger.warning(
                    "Request to openstreetmap failed.\nCode: %s\nContent: %s",
                    response.status_code,
                    response.content,
                )
                raise ValueError("Nominatim returned HTTP %s" % response.status_code)
            result = response.json()
        except Exception as e:
            self._raise_query_error(e)
        return result

    @api.model
    def _call_googlemap(self, addr, **kw):
        """Use google maps API. It won't work without a valid API key.
        :return: (latitude, longitude) or None if not found
        """
        apikey = self.env["credential.credential"]._get_system_secret(
            "geocoding.google_map_api_key"
        )
        if not apikey:
            raise UserError(
                _(
                    "API key for GeoCoding (Places) required.\n"
                    "Visit https://developers.google.com/maps/documentation/geocoding/get-api-key for more information."
                )
            )
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"sensor": "false", "address": addr, "key": apikey}
        if kw.get("force_country"):
            country = self.env["res.country"].search(
                [("name", "=", kw["force_country"])], limit=1
            )
            params["components"] = "country:%s" % (
                country.code if country else kw["force_country"]
            )
        try:
            response = self.env["ir.egress"].request(
                "GET", url, purpose="geocoding", params=params, timeout=10
            )
            if response.status_code != 200:
                _logger.warning(
                    "Request to Google Maps failed.\nCode: %s\nContent: %s",
                    response.status_code,
                    response.content,
                )
                raise ValueError("Google Maps returned HTTP %s" % response.status_code)
            result = response.json()
        except Exception as e:
            self._raise_query_error(e)

        try:
            if result["status"] == "ZERO_RESULTS":
                return None
            if result["status"] != "OK":
                _logger.debug(
                    "Invalid Gmaps call: %s - %s",
                    result["status"],
                    result.get("error_message", ""),
                )
                error_msg = _(
                    "Unable to geolocate, received the error:\n%s"
                    "\n\nGoogle made this a paid feature.\n"
                    "You should first enable billing on your Google account.\n"
                    "Then, go to Developer Console, and enable the APIs:\n"
                    "Geocoding, Maps Static, Maps Javascript.\n",
                    result.get("error_message"),
                )
                raise UserError(error_msg)
            geo = result["results"][0]["geometry"]["location"]
            return float(geo["lat"]), float(geo["lng"])
        except KeyError, IndexError, ValueError:
            _logger.debug(
                "Unexpected Gmaps API answer %s", result.get("error_message", "")
            )
            return None

    @api.model
    def _geo_query_address_default(
        self, street=None, zip_code=None, city=None, state=None, country=None
    ):
        address_list = [
            street,
            ("%s %s" % (zip_code or "", city or "")).strip(),
            state,
            country,
        ]
        return ", ".join(filter(None, address_list))

    @api.model
    def _geo_query_address_googlemap(
        self, street=None, zip_code=None, city=None, state=None, country=None
    ):
        return self._geo_query_address_default(
            street=street, zip_code=zip_code, city=city, state=state, country=country
        )

    def _raise_query_error(self, error):
        raise UserError(_("Error with geolocation server: %s", error))

    def _get_localisation(self, latitude, longitude):
        """Return a human-readable "[postcode] city, country" string for the given coordinates.

        :param float latitude: latitude to resolve
        :param float longitude: longitude to resolve
        :return: human-readable location, using request.geoip first and a
            reverse-geocode fallback
        :rtype: str
        """
        # try to get city and/or country from request.geoip first
        # if not possible, get them from latitude and longitude
        city = request.geoip.city.name
        country_code = request.geoip.country_code
        postcode = False
        if not (city and country_code):
            # for now, we use openstreetmap, if needed, we will add a setting like "partner geolocation" that let the
            # user decide wich provider to use to localise the partner.
            result = self._call_openstreetmap_reverse(latitude, longitude)
            if result and (address := result.get("address")):
                country_code = country_code or address.get("country_code")
                city = city or (
                    address.get("city_district")
                    or address.get("town")
                    or address.get("village")
                    or address.get("city")
                )
                postcode = address.get("postcode")

        country = (
            self.env["res.country"].search(
                [("code", "=", country_code.upper())], limit=1
            )
            if country_code
            else False
        )

        res = postcode or ""
        if city:
            res += f" {city}" if res else city
        if country:
            res += f", {country.name}" if res else country.name

        return res or _("Unknown")
