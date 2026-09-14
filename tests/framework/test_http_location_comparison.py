from types import SimpleNamespace

import odoo.init  # noqa: F401  imported for the bootstrap side effect
from odoo.tests.http import HttpCase

CASE = SimpleNamespace(base_url=lambda: "http://127.0.0.1:8069")


def location(url):
    return HttpCase.parse_http_location(CASE, url)


def test_the_order_of_distinct_parameters_does_not_change_a_location():
    assert location("/my/record/3?access_token=t&pid=7&hash=h") == location(
        "/my/record/3?access_token=t&hash=h&pid=7"
    )


def test_repeated_values_of_one_parameter_keep_their_order():
    assert location("/web?tag=a&tag=b") != location("/web?tag=b&tag=a")


def test_a_different_value_is_still_a_different_location():
    assert location("/my/record/3?pid=7&hash=h") != location(
        "/my/record/3?pid=8&hash=h"
    )


def test_a_relative_location_resolves_against_the_test_server():
    assert location("/my") == location("http://127.0.0.1:8069/my")
