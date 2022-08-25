#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path

try:
    import GeoIP    # Legacy
except ImportError:
    GeoIP = None

try:
    import geoip2
    import geoip2.database
except ImportError:
    geoip2 = None

class GeoIPResolver(object):
    def __init__(self, fname):
        self.fname = fname
        try:
            self._db = geoip2.database.Reader(fname)
            self.version = 2
        except Exception:
            try:
                self._db = GeoIP.open(fname, GeoIP.GEOIP_STANDARD)
                self.version = 1
                assert self._db.database_info is not None
            except Exception:
                raise ValueError('Invalid GeoIP database: %r' % fname)

    def __del__(self):
        if self.version == 2:
            self._db.close()

    @classmethod
    def open(cls, fname):
        if not GeoIP and not geoip2:
            return None
        if not os.path.exists(fname):
            return None
        return GeoIPResolver(fname)

    def resolve(self, ip):
        if self.version == 1:
            return self._db.record_by_addr(ip) or {}
        elif self.version == 2:
            try:
                r = self._db.city(ip)
            except (ValueError, geoip2.errors.AddressNotFoundError):
                return {}
            # Compatibility with Legacy database.
            # Some ips cannot be located to a specific country. Legacy DB used to locate them in
            # continent instead of country. Do the same to not change behavior of existing code.
            country, attr = (r.country, 'iso_code') if r.country.geoname_id else (r.continent, 'code')
            return {
                'city': r.city.name,
                'country_code': getattr(country, attr),
                'country_name': country.name,
                'latitude': r.location.latitude,
                'longitude': r.location.longitude,
                'region': r.subdivisions[0].iso_code if r.subdivisions else None,
                'time_zone': r.location.time_zone,
            }

    # compat
    def record_by_addr(self, addr):
        return self.resolve(addr)
