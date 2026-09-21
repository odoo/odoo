"""One parse of an ORDER BY string, shared by the three readers that each
used to run the regex themselves and re-derive desc/nulls from it."""

import pytest

from odoo.orm.parsing import OrderTerm, parse_order


def terms_of(order: str) -> tuple[OrderTerm, ...]:
    parsed = parse_order(order)
    assert parsed is not None, f"{order!r} was expected to parse"
    return parsed


def test_a_bare_field_is_ascending_with_nulls_last():
    (term,) = terms_of("name")
    assert (term.field, term.property, term.func) == ("name", None, None)
    assert term.desc is False
    assert term.nulls_first is False


def test_descending_puts_nulls_first_by_default():
    (term,) = terms_of("name desc")
    assert term.desc is True
    assert term.nulls_first is True


@pytest.mark.parametrize("order", ["name DESC", "name Desc", "  name   desc  "])
def test_direction_is_case_insensitive_and_space_tolerant(order):
    (term,) = terms_of(order)
    assert term.desc is True


def test_an_explicit_nulls_clause_wins_over_the_default():
    (term,) = terms_of("name desc nulls last")
    assert term.desc is True
    assert term.nulls_first is False
    (term,) = terms_of("name nulls first")
    assert term.desc is False
    assert term.nulls_first is True


def test_every_term_is_returned_in_order():
    terms = terms_of("a desc, b, c nulls first")
    assert [t.field for t in terms] == ["a", "b", "c"]
    assert [t.desc for t in terms] == [True, False, False]
    assert [t.nulls_first for t in terms] == [True, False, True]


def test_a_property_and_a_granularity_are_carried():
    (term,) = terms_of("attributes.colour desc")
    assert (term.field, term.property) == ("attributes", "colour")
    (term,) = terms_of("date:month")
    assert (term.field, term.func) == ("date", "month")


@pytest.mark.parametrize(
    "order", ["name ))", "name desc extra", "", "name,", ",name", "name asc desc"]
)
def test_an_order_that_does_not_parse_is_none_rather_than_a_partial_answer(order):
    assert parse_order(order) is None


def test_the_same_string_is_parsed_once():
    parse_order.cache_clear()
    parse_order("name desc, id")
    hits_before = parse_order.cache_info().hits
    parse_order("name desc, id")
    parse_order("name desc, id")
    assert parse_order.cache_info().hits == hits_before + 2
