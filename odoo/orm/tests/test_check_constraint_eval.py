"""The CHECK evaluator must refuse only what PostgreSQL refuses.

A CHECK that evaluates to NULL passes in SQL, and anything outside the
grammar must be treated as unknown, so `violates_check` answering True is a
claim that the database would raise.
"""

import pytest

from odoo.orm.runtime._check_constraints import violates_check


@pytest.mark.parametrize(
    ("definition", "row"),
    [
        ("CHECK(color >= 0)", {"color": -1}),
        ("check(rating >= 0 and rating <= 5)", {"rating": 6}),
        ("check(rating >= 0 and rating <= 5)", {"rating": -1}),
        ("CHECK(vote IN (-1, 0, 1))", {"vote": 2}),
        ("CHECK (channel_id IS NOT NULL)", {"channel_id": None}),
        ("check(folder_id <> id)", {"folder_id": 4, "id": 4}),
        ("CHECK(name = 'ok')", {"name": "no"}),
        ("CHECK(a > 0 OR b > 0)", {"a": 0, "b": 0}),
        ("CHECK(NOT (a > 0))", {"a": 1}),
    ],
)
def test_a_row_the_database_refuses_is_refused(definition, row):
    assert violates_check(definition, row) is True


@pytest.mark.parametrize(
    ("definition", "row"),
    [
        ("CHECK(color >= 0)", {"color": 0}),
        ("CHECK(color >= 0)", {"color": 5}),
        ("check(rating >= 0 and rating <= 5)", {"rating": 3}),
        ("CHECK(vote IN (-1, 0, 1))", {"vote": 0}),
        ("CHECK (channel_id IS NOT NULL)", {"channel_id": 7}),
        ("check(folder_id <> id)", {"folder_id": 4, "id": 5}),
        ("CHECK(a > 0 OR b > 0)", {"a": 0, "b": 1}),
    ],
)
def test_a_row_the_database_accepts_is_accepted(definition, row):
    assert violates_check(definition, row) is False


@pytest.mark.parametrize(
    ("definition", "row"),
    [
        # NULL makes the comparison unknown, and an unknown CHECK passes
        ("CHECK(color >= 0)", {"color": None}),
        ("check(rating >= 0 and rating <= 5)", {"rating": None}),
        ("CHECK(vote IN (-1, 0, 1))", {"vote": None}),
        ("check(folder_id <> id)", {"folder_id": None, "id": 4}),
        # a column the row does not carry
        ("CHECK(color >= 0)", {"other": 1}),
        # outside the grammar
        ("CHECK(lower(name) = name)", {"name": "x"}),
        # a parenthesised boolean as a comparison operand: three such
        # constraints exist in the workspace and the grammar declines them
        (
            "CHECK((product_id IS NULL) != (package_type_id IS NULL))",
            {"product_id": None, "package_type_id": None},
        ),
        ("CHECK(a @> b)", {"a": 1, "b": 2}),
        ("EXCLUDE USING gist (x WITH =)", {"x": 1}),
        ("unique(code)", {"code": "a"}),
        ("CHECK(", {"a": 1}),
        # a comparison Python cannot make is unknown, not a violation
        ("CHECK(name >= 0)", {"name": "text"}),
    ],
)
def test_what_cannot_be_established_is_not_a_violation(definition, row):
    assert violates_check(definition, row) is False


def test_an_or_with_one_unknown_side_still_passes_when_the_other_is_true():
    assert violates_check("CHECK(a IS NULL OR a > 0)", {"a": None}) is False
    assert violates_check("CHECK(a IS NULL OR a > 0)", {"a": 5}) is False
    assert violates_check("CHECK(a IS NULL OR a > 0)", {"a": -5}) is True


def test_an_and_with_one_unknown_side_is_unknown_unless_the_other_is_false():
    assert violates_check("CHECK(a > 0 AND b > 0)", {"a": 5, "b": None}) is False
    assert violates_check("CHECK(a > 0 AND b > 0)", {"a": -5, "b": None}) is True
