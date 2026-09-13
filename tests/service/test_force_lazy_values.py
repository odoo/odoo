import pytest

from odoo.service.model import _force_lazy_values
from odoo.tools import lazy


class _ReadonlyMapping:
    def __init__(self, data):
        self._data = dict(data)

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def values(self):
        return self._data.values()


from collections.abc import Mapping  # noqa: E402

Mapping.register(_ReadonlyMapping)


def _gen(*items):
    return (i for i in items)


class TestLaziesAreWarmedWhileTheCursorIsOpen:
    def test_a_top_level_lazy_is_evaluated(self):
        calls = []
        value = lazy(lambda: calls.append(1) or "v")
        _force_lazy_values(value)
        assert calls == [1], "the deferred call did not run inside the walk"

    def test_a_lazy_nested_in_a_dict_is_evaluated(self):
        calls = []
        _force_lazy_values({"k": lazy(lambda: calls.append(1) or 1)})
        assert calls == [1]

    def test_a_lazy_nested_in_a_list_is_evaluated(self):
        calls = []
        _force_lazy_values([[lazy(lambda: calls.append(1) or 1)]])
        assert calls == [1]

    def test_the_lazy_object_itself_is_preserved(self):
        value = lazy(lambda: 1)
        out = _force_lazy_values({"k": value})
        assert out["k"] is value, (
            "the marshaller unwraps `lazy` itself; replacing it here would "
            "change what odoo.tools.json.orjson_default sees"
        )


class TestIteratorsSurviveTheWalk:
    def test_a_top_level_iterator_becomes_a_list(self):
        assert _force_lazy_values(_gen(1, 2, 3)) == [1, 2, 3]

    def test_an_iterator_in_a_dict_is_materialised_not_consumed(self):
        out = _force_lazy_values({"rows": _gen(1, 2, 3)})
        assert out["rows"] == [1, 2, 3], (
            "walking the container consumed the generator and left the "
            "exhausted object in place"
        )

    def test_an_iterator_in_a_list_is_materialised_not_consumed(self):
        out = _force_lazy_values([_gen(1, 2)])
        assert out[0] == [1, 2]

    def test_an_iterator_in_a_tuple_is_materialised(self):
        out = _force_lazy_values((_gen(1, 2),))
        assert isinstance(out, tuple)
        assert out[0] == [1, 2]

    def test_a_deeply_nested_iterator_is_materialised(self):
        out = _force_lazy_values({"a": [{"b": _gen(7)}]})
        assert out["a"][0]["b"] == [7]

    def test_a_lazy_inside_a_materialised_iterator_is_still_warmed(self):
        calls = []
        out = _force_lazy_values({"rows": _gen(lazy(lambda: calls.append(1) or 5))})
        assert calls == [1]
        assert len(out["rows"]) == 1

    def test_an_iterator_we_cannot_replace_is_left_intact(self):
        """Better an untouched object than an exhausted one."""
        gen = _gen(1, 2)
        out = _force_lazy_values(_ReadonlyMapping({"rows": gen}))
        assert list(out["rows"]) == [1, 2], (
            "the walk consumed a generator it had no way to write back"
        )


class TestLazyIsNotMistakenForAnIterator:
    """`lazy` proxies __iter__/__next__, so isinstance(lazy, Iterator) is True."""

    def test_a_lazy_reports_as_an_iterator(self):
        from collections.abc import Iterator

        assert isinstance(lazy(lambda: 1), Iterator), (
            "if this ever stops being true the guards in _force_lazy_in_value can "
            "drop their lazy check -- until then they cannot"
        )

    def test_a_lazy_in_a_values_view_is_still_warmed(self):
        calls = []
        _force_lazy_values({"k": lazy(lambda: calls.append(1) or 1)}.values())
        assert calls == [1]

    def test_a_lazy_in_a_read_only_mapping_is_still_warmed(self):
        calls = []
        _force_lazy_values(_ReadonlyMapping({"k": lazy(lambda: calls.append(1) or 1)}))
        assert calls == [1]

    def test_a_lazy_is_never_replaced_by_the_list_it_would_yield(self):
        value = lazy(lambda: [1, 2])
        out = _force_lazy_values([value])
        assert out[0] is value


class TestTheWalkDoesNotDisturbOrdinaryResults:
    @pytest.mark.parametrize(
        "value",
        [
            None,
            1,
            "s",
            b"b",
            True,
            3.5,
            [1, 2, 3],
            {"a": 1},
            [{"id": 1, "name": "x"}],
            ({"a": [1, {"b": 2}]},),
        ],
    )
    def test_the_object_comes_back_equal(self, value):
        assert _force_lazy_values(value) == value

    def test_a_plain_container_is_the_same_object(self):
        value = [{"id": 1}]
        assert _force_lazy_values(value) is value

    def test_a_string_is_not_walked_character_by_character(self):
        assert _force_lazy_values("abc") == "abc"

    def test_a_set_survives(self):
        assert _force_lazy_values({1, 2}) == {1, 2}

    def test_a_cycle_is_rejected_before_commit(self):
        value: list = []
        value.append(value)
        with pytest.raises(ValueError, match="cyclic"):
            _force_lazy_values(value)

    def test_a_lazy_iterator_keeps_its_materialized_result(self):
        assert _force_lazy_values(lazy(lambda: _gen(1, 2))) == [1, 2]


class TestTheWalkCopiesOnlyWhatItReplaces:
    def test_an_untouched_tree_keeps_every_identity(self):
        import datetime
        import decimal

        row = {
            "id": 1,
            "when": datetime.datetime(2026, 1, 1, 12),
            "day": datetime.date(2026, 1, 1),
            "amount": decimal.Decimal("1.50"),
            "m2o": (3, "Partner"),
            "ids": [1, 2],
        }
        result = {"length": 1, "records": [row]}
        out = _force_lazy_values(result)
        assert out is result
        assert out["records"] is result["records"]
        assert out["records"][0] is row
        assert out["records"][0]["m2o"] is row["m2o"]

    def test_only_the_container_holding_a_replaced_value_is_copied(self):
        untouched = {"a": (1, 2)}
        replaced = {"rows": _gen(1, 2)}
        result = (untouched, replaced)
        out = _force_lazy_values(result)
        assert out is not result
        assert out[0] is untouched
        assert out[1] is not replaced
        assert out[1]["rows"] == [1, 2]
