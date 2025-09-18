"""Database-free tests for ``res.country`` and ``res.country.state``.

Tests ``_compute_image_url()``, ``get_address_fields()``, and state
display name formatting.

Run with::

    python -m pytest core/tests/models/test_res_country.py -v
"""


# ── _compute_image_url ───────────────────────────────────────────


class TestImageUrl:
    """``_compute_image_url``: country code to flag URL."""

    def test_standard_code(self, make_country):
        mx = make_country("Mexico", "MX")
        mx._compute_image_url()
        assert mx.image_url == "/base/static/img/country_flags/mx.png"

    def test_no_code(self, env):
        """Country without a code gets no flag."""
        country = env["res.country"].create({"name": "Unknown", "code": ""})
        country._compute_image_url()
        assert not country.image_url

    def test_flag_mapping_gf(self, make_country):
        """French Guiana (GF) maps to French flag (fr)."""
        gf = make_country("French Guiana", "GF")
        gf._compute_image_url()
        assert gf.image_url == "/base/static/img/country_flags/fr.png"

    def test_flag_mapping_um(self, make_country):
        """US Minor Outlying Islands (UM) maps to US flag."""
        um = make_country("US Minor Islands", "UM")
        um._compute_image_url()
        assert um.image_url == "/base/static/img/country_flags/us.png"

    def test_no_flag_country_aq(self, make_country):
        """Antarctica (AQ) has no flag."""
        aq = make_country("Antarctica", "AQ")
        aq._compute_image_url()
        assert not aq.image_url

    def test_no_flag_country_sj(self, make_country):
        """Svalbard and Jan Mayen (SJ) has no flag."""
        sj = make_country("Svalbard", "SJ")
        sj._compute_image_url()
        assert not sj.image_url

    def test_lowercase_in_url(self, make_country):
        """URL always uses lowercase code."""
        us = make_country("United States", "US")
        us._compute_image_url()
        assert "/us.png" in us.image_url


# ── get_address_fields ───────────────────────────────────────────


class TestAddressFields:
    """``get_address_fields()``: extract ``%(field)s`` placeholders."""

    def test_default_format(self, env):
        fmt = "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        country = env["res.country"].create(
            {"name": "US", "code": "US", "address_format": fmt}
        )
        fields = country.get_address_fields()
        assert fields == [
            "street", "street2", "city", "state_code", "zip", "country_name",
        ]

    def test_minimal_format(self, make_country):
        country = make_country(address_format="%(city)s\n%(country_name)s")
        fields = country.get_address_fields()
        assert fields == ["city", "country_name"]

    def test_no_fields(self, make_country):
        country = make_country(address_format="Just plain text")
        assert country.get_address_fields() == []

    def test_japanese_format(self, env):
        """Japanese format: zip before city, state before street."""
        fmt = "〒%(zip)s\n%(state_name)s%(city)s\n%(street)s\n%(street2)s"
        country = env["res.country"].create(
            {"name": "Japan", "code": "JP", "address_format": fmt}
        )
        fields = country.get_address_fields()
        assert fields == ["zip", "state_name", "city", "street", "street2"]


# ── ResCountryState._compute_display_name ────────────────────────


class TestStateDisplayName:
    """``ResCountryState._compute_display_name``."""

    def test_state_with_country_code(self, make_country, env):
        mx = make_country("Mexico", "MX")
        state = env["res.country.state"].create(
            {"name": "Jalisco", "code": "JAL", "country_id": mx.id}
        )
        state._compute_display_name()
        assert "Jalisco" in state.display_name
        assert "MX" in state.display_name

    def test_formatted_display_name(self, make_country, env):
        """Context flag ``formatted_display_name`` changes format."""
        mx = make_country("Mexico", "MX")
        state = env["res.country.state"].create(
            {"name": "Jalisco", "code": "JAL", "country_id": mx.id}
        )
        state_ctx = state.with_context(formatted_display_name=True)
        state_ctx._compute_display_name()
        assert "--JAL--" in state_ctx.display_name or "--MX--" in state_ctx.display_name
