# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import time

import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org"
TIMEOUT = 2.5
MAX_RETRIES = 0


class OSMAddressAutoCompleteController(http.Controller):

    def _is_retryable_http_status(self, status_code):
        return status_code in (408, 409, 425, 429, 500, 502, 503, 504)

    def _extract_lat_lon(self, result):
        if not isinstance(result, dict):
            return None, None

        lat = result.get("lat")
        lon = result.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)

        centroid = result.get("centroid")
        if isinstance(centroid, dict) and centroid.get("type") == "Point":
            coords = centroid.get("coordinates") or []
            if len(coords) >= 2:
                return float(coords[1]), float(coords[0])

        geometry = result.get("geometry")
        if isinstance(geometry, dict) and geometry.get("type") == "Point":
            coords = geometry.get("coordinates") or []
            if len(coords) >= 2:
                return float(coords[1]), float(coords[0])

        return None, None

    def _get_min_query_len(self):
        return int(
            request.env["ir.config_parameter"].sudo().get_param(
                "osm_address_autocomplete.minimal_partial_address_size", "3"
            )
        )

    def _get_user_agent(self):
        return request.env["ir.config_parameter"].sudo().get_param(
            "osm_address_autocomplete.user_agent",
            "OdooOSMAutocomplete/1.0 (+https://odoo.local; contact: admin@localhost)",
        )

    def _get_nominatim_endpoint(self):
        return request.env["ir.config_parameter"].sudo().get_param(
            "osm_address_autocomplete.endpoint",
            NOMINATIM_ENDPOINT,
        )

    def _get_timeout(self):
        value = request.env["ir.config_parameter"].sudo().get_param(
            "osm_address_autocomplete.timeout",
            str(TIMEOUT),
        )
        try:
            return max(1.0, float(value))
        except (TypeError, ValueError):
            return TIMEOUT

    def _get_max_retries(self):
        value = request.env["ir.config_parameter"].sudo().get_param(
            "osm_address_autocomplete.max_retries",
            str(MAX_RETRIES),
        )
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return MAX_RETRIES

    def _get_accept_language(self):
        lang = request.env.user.lang or "es_ES"
        return lang.replace("_", "-")

    def _get_country_code(self, country_id):
        if not country_id:
            return None
        country = request.env["res.country"].browse(country_id)
        return country.code if country.exists() else None

    def _nominatim_get(self, route, params):
        headers = {
            "User-Agent": self._get_user_agent(),
            "Accept-Language": self._get_accept_language(),
        }
        endpoint = self._get_nominatim_endpoint().rstrip("/")
        timeout = self._get_timeout()
        max_retries = self._get_max_retries()
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                response = requests.get(
                    f"{endpoint}{route}",
                    params=params,
                    headers=headers,
                    timeout=(2.5, timeout),
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as exc:
                last_exc = exc
                status = exc.response.status_code if exc.response else None
                if status and not self._is_retryable_http_status(status):
                    break
                if attempt < max_retries:
                    time.sleep(min(0.3 * (attempt + 1), 0.9))
            except (ValueError, requests.RequestException) as exc:
                last_exc = exc
                if attempt < max_retries:
                    time.sleep(min(0.3 * (attempt + 1), 0.9))
        _logger.warning("OSM request failed: %s", last_exc)
        raise last_exc

    def _build_simplified_display_for_search(self, address):
        """Construye un display simplificado para el autocomplete: calle, número, ciudad, código postal, provincia"""
        if not isinstance(address, dict):
            return None
        
        parts = []
        
        # Calle y número
        road = address.get("road")
        house_number = address.get("house_number")
        if road:
            street_part = road
            if house_number:
                street_part += f" {house_number}"
            parts.append(street_part)
        
        # Ciudad
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("hamlet")
            or address.get("locality")
        )
        if city:
            parts.append(city)

        # Código postal
        postcode = address.get("postcode")
        if postcode:
            parts.append(postcode)
        
        # Provincia/Estado
        state = address.get("state") or address.get("region") or address.get("state_district")
        if state:
            parts.append(state)
        
        return ", ".join(parts) if parts else None

    def _translate_nominatim_to_standard(self, address):
        if isinstance(address, list):
            address = address[0] if address else {}

        standard = {}

        def _build_street2(addr):
            suffix_parts = [
                addr.get("entrance"),
                addr.get("staircase"),
                addr.get("level"),
                addr.get("floor"),
                addr.get("unit"),
            ]
            return " ".join([p for p in suffix_parts if p]).strip()

        def _build_simplified_street(addr):
            road = addr.get("road")
            house_number = addr.get("house_number")
            parts = [p for p in [road, house_number] if p]
            suffix_parts = [
                addr.get("entrance"),
                addr.get("staircase"),
                addr.get("level"),
                addr.get("floor"),
                addr.get("unit"),
            ]
            suffix = " ".join([p for p in suffix_parts if p])
            if suffix:
                parts.append(suffix)
            return " ".join(parts).strip()

        # 1. PAÍS
        country_code = address.get("country_code") if isinstance(address, dict) else None
        country_id = None
        if country_code:
            country = request.env["res.country"].search(
                [("code", "=", country_code.upper())], limit=1
            )
            if country:
                standard["country"] = [country.id, country.name]
                country_id = country.id

        # 2. CIUDAD
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("hamlet")
            or address.get("locality")
        )
        if city:
            standard["city"] = city

        # 3. CÓDIGO POSTAL
        postcode = address.get("postcode")
        if postcode:
            standard["zip"] = postcode

        # 4. CALLE Y NÚMERO
        street = (
            address.get("road")
            or address.get("pedestrian")
            or address.get("footway")
            or address.get("path")
        )
        number = address.get("house_number")
        
        # Separar calle y número
        if street:
            standard["street"] = street
        if number:
            standard["street_number"] = number

        street2 = _build_street2(address) if isinstance(address, dict) else ""
        if street2:
            standard["street2"] = street2

        # 5. CALLE SIMPLIFICADA (para mostrar en el autocomplete)
        simplified_street = _build_simplified_street(address) if isinstance(address, dict) else ""
        if simplified_street:
            standard["formatted_street_number"] = simplified_street
        else:
            formatted_parts = []
            if standard.get("street"):
                formatted_parts.append(standard["street"])
            if standard.get("street2"):
                formatted_parts.append(standard["street2"])
            if formatted_parts:
                standard["formatted_street_number"] = ", ".join(formatted_parts)

        # 6. PROVINCIA/ESTADO
        state_name = (
            address.get("state")
            or address.get("region")
            or address.get("state_district")
            or address.get("province")
        )
        
        if state_name:
            # Intentar vincularlo con un estado conocido en Odoo
            state = None
            
            # Primero intenta con el país identificado
            if country_id:
                state = request.env["res.country.state"].search(
                    [
                        ("name", "ilike", state_name),
                        ("country_id", "=", country_id),
                    ],
                    limit=1,
                )
            
            # Si no encuentra o no hay país, intenta sin filtro de país
            if not state:
                state = request.env["res.country.state"].search(
                    [("name", "ilike", state_name)],
                    limit=1,
                )
            
            # Si lo encontró en la BD, devuelve como [id, name]
            if state:
                standard["state"] = [state.id, state.name]
            else:
                # Si no lo encontró, devuelve el nombre como texto (fallback)
                standard["state_name"] = state_name

        _logger.info(f"OSM Translate Response: {standard}")
        return standard

    def _perform_place_search(self, partial_address, country_id=None, city_name=None, state_name=None):
        min_len = self._get_min_query_len()
        if len(partial_address) <= min_len:
            return {"results": []}

        has_number = bool(re.search(r"\b\d+[A-Za-z]?\b", partial_address))

        # Construir query más específico con ciudad y provincia si están disponibles
        query_parts = [partial_address]
        if state_name and state_name.strip():
            query_parts.append(state_name.strip())
        if city_name and city_name.strip():
            query_parts.append(city_name.strip())
        
        query = ", ".join(query_parts)

        if has_number:
            params = {
                "street": partial_address,
                "format": "json",
                "addressdetails": 1,
                "limit": 12,
                "dedupe": 0,
            }
            if city_name and city_name.strip():
                params["city"] = city_name.strip()
            if state_name and state_name.strip():
                params["state"] = state_name.strip()
        else:
            params = {
                "q": query,
                "format": "json",
                "addressdetails": 1,
                "limit": 12,
                "dedupe": 0,
            }
        country_code = self._get_country_code(country_id)
        if country_code:
            params["countrycodes"] = country_code.lower()

        try:
            results = self._nominatim_get("/search", params)
        except (TimeoutError, ValueError, requests.RequestException) as exc:
            _logger.info("OSM autocomplete search unavailable: %s", exc)
            return {"results": []}

        unique_results = []
        seen = set()
        for result in results or []:
            formatted = self._build_simplified_display_for_search(result.get("address", {})) or result.get("display_name")
            place_id = result.get("place_id")
            key = (formatted or "", place_id or "")
            if key in seen:
                continue
            seen.add(key)
            unique_results.append({
                "formatted_address": formatted,
                "place_id": place_id,
            })

        return {"results": unique_results}

    def _perform_place_details(self, place_id):
        params = {
            "place_id": place_id,
            "format": "json",
            "addressdetails": 1,
        }
        try:
            result = self._nominatim_get("/details", params)
        except (TimeoutError, ValueError, requests.RequestException) as exc:
            _logger.info("OSM autocomplete details unavailable: %s", exc)
            return {}

        address = result.get("address") or {}
        standard = self._translate_nominatim_to_standard(address)

        full_address_parts = []
        if standard.get("street"):
            full_address_parts.append(standard["street"])
        if standard.get("street2"):
            full_address_parts.append(standard["street2"])
        if standard.get("zip"):
            full_address_parts.append(standard["zip"])
        if standard.get("city"):
            full_address_parts.append(standard["city"])
        if standard.get("state"):
            full_address_parts.append(standard["state"][1])
        elif standard.get("state_name"):
            full_address_parts.append(standard["state_name"])
        if standard.get("country"):
            full_address_parts.append(standard["country"][1])
        if full_address_parts:
            standard["full_address"] = ", ".join(full_address_parts)

        display_name = result.get("display_name") if isinstance(result, dict) else None
        if display_name and not standard.get("formatted_street_number"):
            standard["formatted_street_number"] = display_name
            standard.setdefault("street", display_name)

        # Obtener coordenadas del resultado de Nominatim
        lat, lon = self._extract_lat_lon(result)
        if lat is None or lon is None:
            try:
                lookup = self._nominatim_get(
                    "/lookup",
                    {
                        "place_id": place_id,
                        "format": "json",
                        "addressdetails": 1,
                    },
                )
            except (TimeoutError, ValueError, requests.RequestException) as exc:
                _logger.info("OSM lookup unavailable: %s", exc)
                lookup = None

            if isinstance(lookup, list) and lookup:
                lat, lon = self._extract_lat_lon(lookup[0])
                if not standard and isinstance(lookup[0], dict):
                    lookup_address = lookup[0].get("address") or {}
                    standard.update(self._translate_nominatim_to_standard(lookup_address))

        if lat is None or lon is None:
            search_label = standard.get("full_address") or display_name
            if search_label:
                try:
                    search = self._nominatim_get(
                        "/search",
                        {
                            "q": search_label,
                            "format": "json",
                            "addressdetails": 1,
                            "limit": 1,
                        },
                    )
                except (TimeoutError, ValueError, requests.RequestException) as exc:
                    _logger.info("OSM search fallback unavailable: %s", exc)
                    search = None

                if isinstance(search, list) and search:
                    lat, lon = self._extract_lat_lon(search[0])
                    if not standard and isinstance(search[0], dict):
                        search_address = search[0].get("address") or {}
                        standard.update(self._translate_nominatim_to_standard(search_address))

        if lat is not None and lon is not None:
            standard["latitude"] = lat
            standard["longitude"] = lon
        return standard

    @http.route("/osm/autocomplete/address", methods=["POST"], type="json", auth="user")
    def autocomplete_address(self, partial_address, country_id=None, city_name=None, state_name=None):
        return self._perform_place_search(partial_address, country_id=country_id, city_name=city_name, state_name=state_name)

    @http.route("/osm/autocomplete/details", methods=["POST"], type="json", auth="user")
    def autocomplete_details(self, place_id, country_id=None):
        return self._perform_place_details(place_id)
