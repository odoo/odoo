from odoo.http.geoip import _GEOIP_NULL, _GeoIPNull


def test_null_sentinel_is_chainable_and_falsy():
    n = _GeoIPNull()
    assert n.country.iso_code.anything is n
    assert n.location.latitude is n
    assert bool(n) is False


def test_null_sentinel_equals_none_only():
    assert (_GEOIP_NULL == None) is True  # noqa: E711  the sentinel's __eq__(None) IS the subject
    assert (_GEOIP_NULL != None) is False  # noqa: E711  same: `is not None` would test nothing
    assert _GEOIP_NULL.__eq__(object()) is False
    assert _GEOIP_NULL.__eq__(_GEOIP_NULL) is True


def test_null_sentinel_empty_container_protocol():
    assert len(_GEOIP_NULL) == 0
    assert list(_GEOIP_NULL) == []
    assert str(_GEOIP_NULL) == ""
    import pytest

    with pytest.raises(IndexError):
        _ = _GEOIP_NULL[0]


def test_null_sentinel_hashes_like_none():
    assert hash(_GEOIP_NULL) == hash(None)


def test_model_attr_sets_match_real_geoip2():
    import pytest

    from odoo.http import geoip as geoip_mod

    if geoip_mod.geoip2 is None:
        pytest.skip("geoip2 not installed")

    def real(o):
        return {
            a for a in dir(o) if not a.startswith("_") and not callable(getattr(o, a))
        }

    country = real(geoip_mod.geoip2.models.Country({}))
    city = real(geoip_mod.geoip2.models.City({}))
    assert frozenset(country) == geoip_mod._GEOIP_COUNTRY_MODEL_ATTRS
    assert frozenset(city - country) == geoip_mod._GEOIP_CITY_ONLY_MODEL_ATTRS


def test_getattr_typo_raises_even_without_geoip2():
    import types

    import pytest

    from odoo.http import geoip as geoip_mod
    from odoo.http.geoip import _GEOIP_NULL, GeoIP

    app = types.SimpleNamespace(geoip_city_db=None, geoip_country_db=None)
    saved = (
        geoip_mod.geoip2,
        geoip_mod.GEOIP_EMPTY_COUNTRY,
        geoip_mod.GEOIP_EMPTY_CITY,
    )
    geoip_mod.geoip2 = None
    geoip_mod.GEOIP_EMPTY_COUNTRY = _GEOIP_NULL
    geoip_mod.GEOIP_EMPTY_CITY = _GEOIP_NULL
    try:
        geo = GeoIP("127.0.0.1", app=app)
        assert geo.location is _GEOIP_NULL
        assert geo.country is _GEOIP_NULL
        with pytest.raises(AttributeError):
            _ = geo.locatoin
    finally:
        geoip_mod.geoip2, geoip_mod.GEOIP_EMPTY_COUNTRY, geoip_mod.GEOIP_EMPTY_CITY = (
            saved
        )


def _app():
    import types

    return types.SimpleNamespace(geoip_city_db=None, geoip_country_db=None)


def test_geoip_does_not_claim_a_mapping_it_cannot_honour():
    import collections.abc

    from odoo.http.geoip import GeoIP

    geoip = GeoIP("1.2.3.4", app=_app())

    assert not isinstance(geoip, collections.abc.Mapping)


def test_the_indexing_api_three_callers_still_use_keeps_working():
    from odoo.http.geoip import GeoIP

    geoip = GeoIP("1.2.3.4", app=_app())

    assert geoip["country_name"] is None
    assert geoip.get("country_name") is None
    assert geoip.get("country_name", "fallback") is None
    assert geoip.get("not_a_geoip_key", "fallback") == "fallback"
    assert "country_code" in geoip
    assert "not_a_geoip_key" not in geoip


def test_the_application_opens_no_reader_for_a_missing_database(tmp_path):
    from odoo.http import settings
    from odoo.http.application import Application

    app = Application()
    with settings.override(
        geoip_city_db=str(tmp_path / "absent.mmdb"),
        geoip_country_db=str(tmp_path / "absent.mmdb"),
    ):
        assert app.geoip_city_db is None
        assert app.geoip_country_db is None


def test_the_application_opens_no_reader_for_a_corrupt_database(tmp_path):
    from odoo.http import settings
    from odoo.http.application import Application

    corrupt = tmp_path / "corrupt.mmdb"
    corrupt.write_bytes(b"not a maxmind database")
    app = Application()
    with settings.override(geoip_city_db=str(corrupt), geoip_country_db=str(corrupt)):
        assert app.geoip_city_db is None
        assert app.geoip_country_db is None
