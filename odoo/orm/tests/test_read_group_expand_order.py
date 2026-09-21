"""`group_expand` puts the groups the query did not return back in order.
Which order is decided by the caller's `order` string, and that string is
written in more than one way -- so it is parsed, not spelled out."""

import pytest

from odoo.orm.models.mixins.read_group.fill import _orders_descending_by


@pytest.mark.parametrize(
    "order",
    [
        "stage_id desc",
        "stage_id DESC",
        "stage_id Desc",
        "  stage_id   desc  ",
        "stage_id desc, id",
        "stage_id desc,id asc",
        "stage_id desc nulls last",
        "stage_id DESC NULLS FIRST, id",
    ],
)
def test_every_spelling_of_descending_by_the_groupby_is_descending(order):
    assert _orders_descending_by(order, "stage_id") is True


@pytest.mark.parametrize(
    "order",
    [
        None,
        "",
        "stage_id",
        "stage_id asc",
        "stage_id ASC, id desc",
        "id desc, stage_id desc",
        "other_id desc",
        "stage_id_2 desc",
    ],
)
def test_anything_else_is_not_descending_by_the_groupby(order):
    assert _orders_descending_by(order, "stage_id") is False


def test_a_granularity_spec_is_matched_whole():
    assert _orders_descending_by("date:month desc", "date:month") is True
    assert _orders_descending_by("date:month desc", "date:day") is False
    assert _orders_descending_by("date desc", "date:month") is False


def test_an_unparsable_order_is_not_descending():
    assert _orders_descending_by("stage_id ))", "stage_id") is False
