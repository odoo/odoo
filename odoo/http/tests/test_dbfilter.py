from odoo.http import _dbfilter
from odoo.http._dbfilter import _normalize_dbfilter_host
from odoo.tools import config


def test_normalize_dbfilter_host_strips_port_www_and_lowercases():
    assert _normalize_dbfilter_host("WWW.Example.COM:8069") == "example.com"
    assert _normalize_dbfilter_host("example.com") == "example.com"
    assert _normalize_dbfilter_host("WWW.sub.example.com") == "sub.example.com"


def test_normalize_dbfilter_host_ipv6_keeps_brackets():
    assert _normalize_dbfilter_host("[::1]:8069") == "[::1]"
    assert _normalize_dbfilter_host("[2001:DB8::1]") == "[2001:db8::1]"
    assert _normalize_dbfilter_host("[::1") == "[::1"


def test_dbfilter_host_normalized_exactly_once():
    from odoo.http._dbfilter import _compile_dbfilter, filter_dbs_served
    from odoo.tools import config

    saved = config["dbfilter"]
    config["dbfilter"] = "^%h$"
    _compile_dbfilter.cache_clear()
    try:
        assert filter_dbs_served(["www.example.com"], host="www.www.example.com") == [
            "www.example.com"
        ]
        assert filter_dbs_served(["example.com"], host="www.www.example.com") == []
    finally:
        config["dbfilter"] = saved
        _compile_dbfilter.cache_clear()


def test_db_filter_without_request_uses_empty_host():
    from odoo.http._dbfilter import filter_dbs_served
    from odoo.tools import config

    saved = config["dbfilter"]
    config["dbfilter"] = "^%d$"
    try:
        assert filter_dbs_served(["somedb"]) == []
    finally:
        config["dbfilter"] = saved


def _reset_dbfilter_caches():
    _dbfilter._compile_dbfilter.cache_clear()
    _dbfilter._has_host_placeholder.cache_clear()


def test_a_dbfilter_that_ignores_the_host_caches_one_regex_for_every_host():
    _dbfilter._compile_dbfilter.cache_clear()
    with config.patch(dbfilter=".*", db_name=[]):
        for i in range(600):
            _dbfilter.filter_dbs_served(["somedb"], host=f"attacker-{i}.example.com")

    assert _dbfilter._compile_dbfilter.cache_info().currsize == 1


def test_a_dbfilter_that_reads_the_host_still_gets_a_regex_per_host():
    _dbfilter._compile_dbfilter.cache_clear()
    with config.patch(dbfilter="^%d_", db_name=[]):
        assert _dbfilter.filter_dbs_served(["alpha_x"], host="alpha.example.com") == [
            "alpha_x"
        ]
        assert _dbfilter.filter_dbs_served(["alpha_x"], host="beta.example.com") == []

    assert _dbfilter._compile_dbfilter.cache_info().currsize == 2


def test_db_filter_orders_the_same_way_through_both_of_its_filters():
    catalogue = ["zeta", "alpha", "mid"]

    with config.patch(dbfilter=".*", db_name=[]):
        _reset_dbfilter_caches()
        by_pattern = _dbfilter.filter_dbs_served(catalogue, host="x.example")
    with config.patch(dbfilter="", db_name=list(catalogue)):
        _reset_dbfilter_caches()
        by_name = _dbfilter.filter_dbs_served(catalogue, host="x.example")
    with config.patch(dbfilter=".*", db_name=list(catalogue)):
        _reset_dbfilter_caches()
        by_both = _dbfilter.filter_dbs_served(catalogue, host="x.example")

    assert by_pattern == catalogue
    assert by_name == catalogue
    assert by_both == catalogue


def test_db_filter_applies_both_filters_when_both_are_set():
    with config.patch(dbfilter="a.*", db_name=["alpha", "zeta"]):
        _reset_dbfilter_caches()
        assert _dbfilter.filter_dbs_served(
            ["zeta", "alpha", "abc"], host="x.example"
        ) == ["alpha"]
