import threading
from contextlib import suppress
from unittest.mock import MagicMock, patch

import psycopg
import psycopg.errors
import pytest

import odoo.http  # noqa: F401 - see below; imported for its side effect
from odoo.db.errors import PG_RETRY_EXCEPTIONS, PG_RETRY_SQLSTATES
from odoo.service.model import Params

from .conftest import fake_pg_cursor, retrying_env


@pytest.fixture(scope="module")
def mod():
    import odoo.service.model as m

    return m


@pytest.fixture(scope="module")
def tx():
    import odoo.service.transaction as t

    return t


class _FakeIntegrityError(psycopg.errors.IntegrityError):
    def __init__(self, table_name: str = "res_partner") -> None:
        Exception.__init__(self, "unique constraint violated")
        self._pgresult = None
        self._diag_mock = MagicMock()
        self._diag_mock.table_name = table_name
        self.sqlstate = "23505"

    @property
    def diag(self):
        return self._diag_mock


@pytest.fixture
def mock_env():
    return retrying_env()


class _FakeBaseModel:
    _name = "test.model"
    _table = "test_model"


class _FakeModel(_FakeBaseModel):
    def public_method(self) -> str:
        return "public"

    def _underscore(self) -> str:
        return "private"

    def api_private_method(self) -> str:
        return "api_private"

    not_callable = "a string attribute"


_FakeModel.api_private_method._api_private = True


class TestGetPublicMethod:
    @pytest.fixture
    def fake_model(self, mod):
        instance = _FakeModel()
        with patch.object(mod, "BaseModel", _FakeBaseModel):
            yield instance

    def test_underscore_prefix_blocked(self, mod, fake_model) -> None:
        from odoo.exceptions import AccessError

        with pytest.raises(AccessError):
            mod.get_public_method(fake_model, "_underscore")

    def test_unsafe_attribute_blocked(self, mod, fake_model) -> None:
        from odoo.exceptions import AccessError

        with pytest.raises(AccessError):
            mod.get_public_method(fake_model, "__class__")

    def test_api_private_blocked(self, mod, fake_model) -> None:
        from odoo.exceptions import AccessError

        with pytest.raises(AccessError):
            mod.get_public_method(fake_model, "api_private_method")

    def test_non_callable_raises_attribute_error(self, mod, fake_model) -> None:
        with pytest.raises(AttributeError):
            mod.get_public_method(fake_model, "not_callable")

    @pytest.mark.parametrize("name", [123, b"write", None, ("write",), 4.0])
    def test_non_string_method_name_raises_attribute_error(
        self, mod, fake_model, name
    ) -> None:
        with pytest.raises(AttributeError):
            mod.get_public_method(fake_model, name)

    def test_public_method_returned(self, mod, fake_model) -> None:
        method = mod.get_public_method(fake_model, "public_method")
        assert callable(method)
        assert method.__name__ == "public_method"

    def test_api_private_blocked_when_defined_in_base_class(self, mod) -> None:
        from odoo.exceptions import AccessError

        class Base(_FakeBaseModel):
            def deep_private(self) -> str:
                return "from base"

        Base.deep_private._api_private = True

        class Mid(Base):
            pass

        class Leaf(Mid):
            pass

        leaf_instance = Leaf()
        with patch.object(mod, "BaseModel", _FakeBaseModel):
            with pytest.raises(AccessError):
                mod.get_public_method(leaf_instance, "deep_private")


class TestTheNameIsVettedBeforeTheClassIsTouched:
    """A rejected name must not reach `getattr(cls, name)`.

    The name is chosen by the RPC caller and `getattr` on a class runs the
    descriptor protocol, the metaclass included.  The private/unsafe guard is
    the first statement for exactly that reason, and the `_api_private` walk
    reads `__dict__` so a name it rejects never runs a descriptor either.
    """

    @staticmethod
    def _model_whose_metaclass_watches():
        seen = []

        class Watching(type):
            @property
            def evil(cls):
                seen.append("evil")
                return lambda self: "reached"

            @property
            def _underscore(cls):  # private by name
                seen.append("_underscore")
                return lambda self: "reached"

            @property
            def gi_frame(cls):  # in _UNSAFE_ATTRIBUTES
                seen.append("gi_frame")
                return lambda self: "reached"

        class Model(_FakeBaseModel, metaclass=Watching):
            _name = "watched.model"

        return Model, seen

    @pytest.mark.parametrize("name", ["_underscore", "gi_frame"])
    def test_a_rejected_name_never_reaches_the_class(self, mod, name) -> None:
        from odoo.exceptions import AccessError

        Model, seen = self._model_whose_metaclass_watches()
        with patch.object(mod, "BaseModel", _FakeBaseModel):
            with pytest.raises(AccessError):
                mod.get_public_method(Model(), name)
        assert seen == [], (
            f"the metaclass descriptor for {name!r} ran before the guard rejected it"
        )

    def test_an_api_private_name_never_reaches_the_class_either(self, mod) -> None:
        """`_api_private` is read off `__dict__`; a metaclass data descriptor
        of the same name, which `getattr(cls, name)` would prefer, never runs."""
        from odoo.exceptions import AccessError

        seen = []

        class Watching(type):
            @property
            def hidden(cls):
                seen.append("hidden")
                return lambda self: "reached"

        class Model(_FakeBaseModel, metaclass=Watching):
            _name = "watched.model"

            def hidden(self) -> str:
                return "declared"

        Model.__dict__["hidden"]._api_private = True
        with patch.object(mod, "BaseModel", _FakeBaseModel):
            with pytest.raises(AccessError):
                mod.get_public_method(Model(), "hidden")
        assert seen == [], "the _api_private walk ran a descriptor"

    def test_an_accepted_name_still_reaches_the_class(self, mod) -> None:
        Model, seen = self._model_whose_metaclass_watches()
        with patch.object(mod, "BaseModel", _FakeBaseModel):
            mod.get_public_method(Model(), "evil")
        assert seen == ["evil"], "the guard now rejects a public name too"


class TestGetPublicMethodResolvesLive:
    def test_the_class_attribute_is_returned_as_is(self, mod) -> None:
        with patch.object(mod, "BaseModel", _FakeBaseModel):
            first = mod.get_public_method(_FakeModel(), "public_method")
            second = mod.get_public_method(_FakeModel(), "public_method")
        assert first is second is _FakeModel.__dict__["public_method"]

    def test_rebinding_the_method_is_seen_at_once(self, mod) -> None:
        with patch.object(mod, "BaseModel", _FakeBaseModel):
            original = mod.get_public_method(_FakeModel(), "public_method")

            def replacement(self) -> str:
                return "replaced"

            with patch.object(_FakeModel, "public_method", replacement):
                got = mod.get_public_method(_FakeModel(), "public_method")
                assert got is replacement

            assert mod.get_public_method(_FakeModel(), "public_method") is original

    def test_a_rebound_method_is_still_access_checked(self, mod) -> None:
        from odoo.exceptions import AccessError

        with patch.object(mod, "BaseModel", _FakeBaseModel):
            mod.get_public_method(_FakeModel(), "public_method")

            def sneaky(self) -> str:
                return "nope"

            sneaky._api_private = True
            with patch.object(_FakeModel, "public_method", sneaky):
                with pytest.raises(AccessError):
                    mod.get_public_method(_FakeModel(), "public_method")


def _tracked_lazy():
    from odoo.tools import lazy

    state = {"forced": False}

    def fn():
        state["forced"] = True
        return 99

    return lazy(fn), (lambda: state["forced"])


class TestForceLazyValues:
    def test_top_level_lazy_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values(lz)
        assert forced()

    def test_lazy_in_list_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values([1, lz, 3])
        assert forced()

    def test_lazy_in_nested_list_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values([[lz]])
        assert forced()

    def test_lazy_in_tuple_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values((lz,))
        assert forced()

    def test_lazy_as_dict_value_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values({"key": lz})
        assert forced()

    def test_lazy_dict_key_needs_no_walk(self, mod) -> None:
        lz, forced = _tracked_lazy()
        d = {lz: "value"}
        assert forced()
        mod._force_lazy_values(d)
        assert forced()

    def test_lazy_in_set_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values({lz})
        assert forced()

    def test_lazy_in_frozenset_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values(frozenset({lz}))
        assert forced()

    def test_lazy_in_dict_values_view_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values({"k": lz}.values())
        assert forced()

    def test_deeply_nested_lazy_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values({"a": [{"b": (lz,)}]})
        assert forced()

    def test_top_level_generator_materialized_and_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        out = mod._force_lazy_values(x for x in [lz, 2])
        assert isinstance(out, list)
        assert forced()

    def test_nested_generator_forced(self, mod) -> None:
        lz, forced = _tracked_lazy()
        mod._force_lazy_values([(x for x in [lz])])
        assert forced()

    def test_lazy_free_result_returned_unchanged(self, mod) -> None:
        data = [{"id": i, "name": f"r{i}", "active": True, "x": None} for i in range(5)]
        assert mod._force_lazy_values(data) == data

    def test_str_not_descended(self, mod) -> None:
        assert mod._force_lazy_values(["abc"]) == ["abc"]

    def test_str_subclass_does_not_infinite_recurse(self, mod) -> None:
        class MyStr(str):
            __slots__ = ()

        mod._force_lazy_values({"k": MyStr("abcdef")})

    def test_real_lazy_in_odoo_containers_forced(self, mod) -> None:
        from odoo.tools import OrderedSet, frozendict, lazy

        seen = []
        s1, s2, s3 = (lazy(lambda i=i: seen.append(i)) for i in (1, 2, 3))
        result = [
            frozendict({"a": s1, "b": 2, "c": [s2]}),
            OrderedSet([10, 20]),
            {"k": (s3, "txt", 99)},
        ]
        mod._force_lazy_values(result)
        assert sorted(seen) == [1, 2, 3]

    def test_scalar_heavy_collection_still_forces_lazy(self, mod) -> None:
        lz1, f1 = _tracked_lazy()
        lz2, f2 = _tracked_lazy()
        mod._force_lazy_values([1, 2.0, True, None, "s", b"b", lz1, {"x": 3, "y": lz2}])
        assert f1() and f2()

    def test_cyclic_result_fails_before_the_commit(self, mod) -> None:
        cyclic_list: list = [1]
        cyclic_list.append(cyclic_list)
        with pytest.raises(ValueError, match="cyclic"):
            mod._force_lazy_values(cyclic_list)

        cyclic_dict: dict = {}
        cyclic_dict["self"] = cyclic_dict
        with pytest.raises(ValueError, match="cyclic"):
            mod._force_lazy_values(cyclic_dict)

    def test_excessively_nested_result_fails_before_the_commit(self, mod) -> None:
        import sys

        deep: object = "leaf"
        for _ in range(sys.getrecursionlimit() + 500):
            deep = [deep]
        with pytest.raises(ValueError, match="nested too deeply"):
            mod._force_lazy_values(deep)


class TestParamsStr:
    def test_args_preserve_order(self):
        p = Params(["z", "a", "m"], {})
        assert str(p) == "'z', 'a', 'm'"

    def test_kwargs_sorted_alphabetically(self):
        p = Params([], {"z_last": 1, "a_first": 2, "m_middle": 3})
        assert str(p) == "a_first=2, m_middle=3, z_last=1"

    def test_mixed_args_and_kwargs(self):
        p = Params(["first", "second"], {"z": 1, "a": 2})
        assert str(p) == "'first', 'second', a=2, z=1"

    def test_deterministic_across_dict_orderings(self):
        p1 = Params([], dict.fromkeys(["x", "y", "z"], 0))
        p2 = Params([], dict.fromkeys(["z", "x", "y"], 0))
        assert str(p1) == str(p2)


class TestRetrying:
    def test_success_calls_flush_and_commit(self, mod, mock_env) -> None:
        result = mod.retrying(lambda: 42, mock_env)

        assert result == 42
        mock_env.cr.flush.assert_called_once()
        mock_env.cr.commit.assert_called_once()
        mock_env.registry.signal_changes.assert_called_once()

    def test_closed_cursor_skips_flush_and_commit(self, mod, mock_env) -> None:
        mock_env.cr._closed = True
        mock_env.cr.closed = True

        result = mod.retrying(lambda: "done", mock_env)

        assert result == "done"
        mock_env.cr.flush.assert_not_called()
        mock_env.cr.commit.assert_not_called()
        mock_env.registry.signal_changes.assert_not_called()

    def test_plain_operational_error_not_retried(self, mod, mock_env) -> None:
        exc = psycopg.OperationalError("connection reset")
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            raise exc

        with patch("odoo.http") as mock_http:
            mock_http.request = None
            with pytest.raises(psycopg.OperationalError):
                mod.retrying(func, mock_env)

        assert calls == 1

    def test_serialization_failure_retried(self, mod, mock_env) -> None:
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise exc
            return "ok"

        with (
            patch("odoo.http") as mock_http,
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_http.request = None
            mock_backoff.get_delay.return_value = 0.0
            result = mod.retrying(func, mock_env)

        assert result == "ok"
        assert calls == 2

    def test_deadlock_retried(self, mod, mock_env) -> None:
        exc = psycopg.errors.DeadlockDetected()
        exc.sqlstate = "40P01"
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise exc
            return "ok"

        with (
            patch("odoo.http") as mock_http,
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_http.request = None
            mock_backoff.get_delay.return_value = 0.0
            result = mod.retrying(func, mock_env)

        assert result == "ok"
        assert calls == 2

    def test_lock_not_available_retried(self, mod, mock_env) -> None:
        exc = psycopg.errors.LockNotAvailable()
        exc.sqlstate = "55P03"
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise exc
            return "ok"

        with (
            patch("odoo.http") as mock_http,
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_http.request = None
            mock_backoff.get_delay.return_value = 0.0
            result = mod.retrying(func, mock_env)

        assert result == "ok"
        assert calls == 2

    def test_max_retries_exhausted_raises(self, mod, mock_env) -> None:
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"

        def func():
            raise exc

        with (
            patch("odoo.http") as mock_http,
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_http.request = None
            mock_backoff.get_delay.return_value = 0.0
            with pytest.raises(psycopg.errors.SerializationFailure):
                mod.retrying(func, mock_env)

    def test_sleep_called_between_retries_not_on_last(self, mod, tx, mock_env) -> None:
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"
        max_tries = tx.MAX_TRIES_ON_CONCURRENCY_FAILURE

        def func():
            raise exc

        with (
            patch("odoo.http") as mock_http,
            patch("odoo.service.transaction.time") as mock_time,
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_http.request = None
            mock_backoff.get_delay.return_value = 0.0
            with suppress(psycopg.errors.SerializationFailure):
                mod.retrying(func, mock_env)

        assert mock_time.sleep.call_count == max_tries - 1

    def test_integrity_error_converted_to_validation_error(self, mod, mock_env) -> None:
        from odoo.exceptions import ValidationError

        exc = _FakeIntegrityError(table_name="some_table")

        matching_model = MagicMock()
        matching_model._name = "some.model"
        matching_model._table = "some_table"
        matching_model._sql_error_to_message.return_value = "Unique constraint"

        mock_env.registry.values.return_value = [matching_model]
        mock_env.__getitem__ = MagicMock(return_value=matching_model)

        def func():
            raise exc

        with patch("odoo.http") as mock_http:
            mock_http.request = None
            with pytest.raises(
                ValidationError, match="The operation cannot be completed"
            ):
                mod.retrying(func, mock_env)

    def test_integrity_error_with_closed_connection_reraises(
        self, mod, mock_env
    ) -> None:
        exc = _FakeIntegrityError()
        mock_env.cr._closed = False
        mock_env.cr.closed = True

        def func():
            raise exc

        with patch("odoo.http") as mock_http:
            mock_http.request = None
            with pytest.raises(_FakeIntegrityError):
                mod.retrying(func, mock_env)

    @pytest.mark.parametrize(
        ("wrapper_closed", "conn_dead"),
        [
            pytest.param(True, False, id="wrapper-explicitly-closed"),
            pytest.param(False, True, id="underlying-connection-dead"),
            pytest.param(True, True, id="both"),
        ],
    )
    def test_closed_cursor_in_inner_except_reraises_immediately(
        self, mod, mock_env, wrapper_closed, conn_dead
    ) -> None:
        mock_env.cr._closed = wrapper_closed
        mock_env.cr.closed = wrapper_closed or conn_dead
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            raise exc

        with pytest.raises(psycopg.errors.SerializationFailure):
            mod.retrying(func, mock_env)

        assert calls == 1

    def test_concurrency_error_is_retried(self, mod, mock_env) -> None:
        from odoo.exceptions import ConcurrencyError

        calls = 0

        def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise ConcurrencyError("row taken by a concurrent writer")
            return "ok"

        with (
            patch("odoo.http") as mock_http,
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_http.request = None
            mock_backoff.get_delay.return_value = 0.0
            assert mod.retrying(func, mock_env) == "ok"
        assert calls == 2

    def test_a_stale_cached_plan_is_retried(self, mod, mock_env, tx) -> None:
        from odoo.db.errors import is_stale_cached_plan

        exc = psycopg.errors.FeatureNotSupported(
            "cached plan must not change result type"
        )
        from odoo.db.errors import _STALE_PLAN_ATTR

        setattr(exc, _STALE_PLAN_ATTR, True)
        assert is_stale_cached_plan(exc), (
            "premise of this test: the db layer marks a stale plan with this "
            "attribute, and is_stale_cached_plan reads it"
        )
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise exc
            return "ok"

        with (
            patch("odoo.http") as mock_http,
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_http.request = None
            mock_backoff.get_delay.return_value = 0.0
            assert mod.retrying(func, mock_env) == "ok"
        assert calls == 2

    def test_an_integrity_error_on_a_cursor_closed_by_the_rollback_reraises(
        self, mod, mock_env
    ) -> None:
        exc = _FakeIntegrityError()

        def close_the_cursor():
            mock_env.cr.closed = True

        mock_env.cr.rollback = MagicMock(side_effect=close_the_cursor)

        def func():
            raise exc

        with patch("odoo.http") as mock_http:
            mock_http.request = None
            with pytest.raises(psycopg.errors.IntegrityError):
                mod.retrying(func, mock_env)

    def test_failed_rollback_refuses_replay(self, mod, mock_env) -> None:
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"
        mock_env.cr.rollback.side_effect = RuntimeError("rollback failed")
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise exc
            return "ok"

        with (
            patch("odoo.http") as mock_http,
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_http.request = None
            mock_backoff.get_delay.return_value = 0.0
            with pytest.raises(psycopg.errors.SerializationFailure) as caught:
                mod.retrying(func, mock_env)

        assert calls == 1
        assert caught.value.__cause__ is mock_env.cr.rollback.side_effect
        mock_env.cr.commit.assert_not_called()

    def test_outer_except_resets_registry_on_non_retryable_error(
        self, mod, mock_env
    ) -> None:
        exc = ValueError("boom")

        def func():
            raise exc

        with pytest.raises(ValueError, match="boom"):
            mod.retrying(func, mock_env)

        mock_env.transaction.reset.assert_called()
        mock_env.registry.reset_changes.assert_called()

    def test_outer_except_skips_reset_when_connection_closed(
        self, mod, mock_env
    ) -> None:
        mock_env.cr.closed = True
        exc = ValueError("boom")

        def func():
            raise exc

        with pytest.raises(ValueError, match="boom"):
            mod.retrying(func, mock_env)

        mock_env.transaction.reset.assert_not_called()
        mock_env.registry.reset_changes.assert_not_called()

    def test_commit_time_failure_exhausts_bounded_retries(self, mod, mock_env) -> None:
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"
        mock_env.cr.commit.side_effect = exc
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            return "ok"

        with patch("odoo.service.transaction.time.sleep"):
            with pytest.raises(psycopg.errors.SerializationFailure):
                mod.retrying(func, mock_env)

        assert calls == 5
        mock_env.transaction.reset.assert_called()
        mock_env.registry.reset_changes.assert_called()
        mock_env.registry.signal_changes.assert_not_called()

    def test_commit_time_integrity_error_translated_to_validation_error(
        self, mod, mock_env
    ) -> None:
        from odoo.exceptions import ValidationError

        exc = _FakeIntegrityError(table_name="some_table")
        mock_env.cr.commit.side_effect = exc

        matching_model = MagicMock()
        matching_model._name = "some.model"
        matching_model._table = "some_table"
        matching_model._sql_error_to_message.return_value = "Unique constraint"
        mock_env.registry.values.return_value = [matching_model]
        mock_env.__getitem__ = MagicMock(return_value=matching_model)

        with patch("odoo.http") as mock_http:
            mock_http.request = None
            with pytest.raises(
                ValidationError, match="The operation cannot be completed"
            ):
                mod.retrying(lambda: "ok", mock_env)

        mock_env.transaction.reset.assert_called()
        mock_env.registry.reset_changes.assert_called()

    def test_commit_time_integrity_translation_failure_falls_back_to_raw(
        self, mod, mock_env
    ) -> None:
        exc = _FakeIntegrityError(table_name="some_table")
        mock_env.cr.commit.side_effect = exc

        broken_model = MagicMock()
        broken_model._table = "some_table"
        broken_model._sql_error_to_message.side_effect = RuntimeError("dead cursor")
        mock_env.registry.values.return_value = [broken_model]
        mock_env.__getitem__ = MagicMock(return_value=broken_model)

        with patch("odoo.http") as mock_http:
            mock_http.request = None
            with pytest.raises(_FakeIntegrityError):
                mod.retrying(lambda: "ok", mock_env)


class TestIntegrityErrorPicksTheRightModel:
    @staticmethod
    def _model(name, table, message):
        m = MagicMock()
        m._name = name
        m._table = table
        m._sql_error_to_message.return_value = message
        return m

    def _run(self, mod, mock_env, failing_table):
        partner = self._model("res.partner", "res_partner", "partner says no")
        invoice = self._model("account.move", "account_move", "invoice says no")
        base = self._model("base", "base", "base says no")
        by_name = {m._name: m for m in (partner, invoice, base)}

        mock_env.registry.values.return_value = [partner, invoice]
        mock_env.registry.models_by_table = {m._table: m for m in (partner, invoice)}
        mock_env.__getitem__ = MagicMock(side_effect=by_name.__getitem__)

        def func():
            raise _FakeIntegrityError(table_name=failing_table)

        with patch("odoo.http") as mock_http:
            mock_http.request = None
            with pytest.raises(Exception) as excinfo:
                mod.retrying(func, mock_env)
        return str(excinfo.value), by_name

    def test_the_matching_model_formats_the_message(self, mod, mock_env):
        message, _ = self._run(mod, mock_env, "account_move")
        assert "invoice says no" in message
        assert "partner says no" not in message

    def test_a_different_constraint_selects_a_different_model(self, mod, mock_env):
        message, _ = self._run(mod, mock_env, "res_partner")
        assert "partner says no" in message
        assert "invoice says no" not in message

    def test_only_the_matching_model_is_asked_to_format(self, mod, mock_env):
        _message, by_name = self._run(mod, mock_env, "account_move")
        by_name["account.move"]._sql_error_to_message.assert_called_once()
        by_name["res.partner"]._sql_error_to_message.assert_not_called()

    def test_an_unknown_table_falls_back_to_base(self, mod, mock_env):
        message, _by_name = self._run(mod, mock_env, "some_table_nobody_owns")
        assert "base says no" in message


class TestConcurrencyBackoffSchedule:
    def _bounds(self, mod, tx, mock_env):
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"
        bounds = []

        def func():
            raise exc

        with (
            patch("odoo.http") as mock_http,
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_http.request = None
            mock_backoff.get_delay.side_effect = lambda attempt, *, base, cap: (
                bounds.append((0.0, min(base * 2.0 ** (attempt - 1), cap))) or 0.0
            )
            with suppress(psycopg.errors.SerializationFailure):
                mod.retrying(func, mock_env)
        return bounds

    def test_the_bound_doubles_each_attempt_up_to_the_cap(self, mod, tx, mock_env):
        bounds = self._bounds(mod, tx, mock_env)
        assert bounds, "no backoff was computed at all"
        assert bounds == [(0.0, 0.2), (0.0, 0.4), (0.0, 0.8), (0.0, 1.6)]

    def test_the_schedule_is_not_flat(self, mod, tx, mock_env):
        highs = [hi for _lo, hi in self._bounds(mod, tx, mock_env)]
        assert len(set(highs)) > 1, f"backoff is flat: every retry bounded by {highs}"
        assert highs == sorted(highs) and highs[0] < highs[-1]

    def test_the_backoff_is_jittered_from_zero(self, mod, tx, mock_env):
        bounds = self._bounds(mod, tx, mock_env)
        assert bounds
        assert all(lo == 0.0 for lo, _hi in bounds)

    def test_no_wait_ever_exceeds_the_cap(self, mod, tx, mock_env):
        bounds = self._bounds(mod, tx, mock_env)
        cap = tx.MAX_CONCURRENCY_BACKOFF_SECONDS
        assert all(hi <= cap for _lo, hi in bounds), bounds

    def test_one_wait_per_retry_and_none_after_the_last(self, mod, tx, mock_env):
        bounds = self._bounds(mod, tx, mock_env)
        assert len(bounds) == tx.MAX_TRIES_ON_CONCURRENCY_FAILURE - 1


class TestRetryVocabularyMatchesPostgres:
    def test_every_retry_sqlstate_maps_to_an_exception_in_the_tuple(self) -> None:
        for sqlstate in PG_RETRY_SQLSTATES:
            cls = psycopg.errors.lookup(sqlstate)
            assert issubclass(cls, PG_RETRY_EXCEPTIONS), (
                f"sqlstate {sqlstate!r} maps to {cls.__name__}, which is absent "
                f"from PG_RETRY_EXCEPTIONS — retrying() would not "
                f"retry a real error carrying this sqlstate"
            )

    def test_canonical_concurrency_errors_are_recognised(self) -> None:
        for name, sqlstate in [
            ("SerializationFailure", "40001"),
            ("DeadlockDetected", "40P01"),
            ("LockNotAvailable", "55P03"),
        ]:
            cls = getattr(psycopg.errors, name)
            assert issubclass(cls, PG_RETRY_EXCEPTIONS), name
            assert sqlstate in PG_RETRY_SQLSTATES, name

    def test_the_addon_facing_aliases_stay_identical_to_the_canonical_names(
        self, tx
    ) -> None:
        assert tx.PG_CONCURRENCY_EXCEPTIONS_TO_RETRY is PG_RETRY_EXCEPTIONS
        assert tx.PG_CONCURRENCY_ERRORS_TO_RETRY is PG_RETRY_SQLSTATES


class _RecordingParticipant:
    def __init__(self):
        self.rollbacks = []
        self.retries = []
        self.suppress = False

    def on_rollback(self, exc):
        self.rollbacks.append(exc)

    def on_retry(self, exc):
        self.retries.append(exc)

    def is_uncommitted_warning_suppressed(self):
        return self.suppress


@pytest.fixture
def participant():
    return _RecordingParticipant()


class TestRetryParticipantHooks:
    def test_a_retried_failure_fires_both_hooks(self, mod, mock_env, participant):
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise exc
            return "ok"

        with (
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_backoff.get_delay.return_value = 0.0
            assert mod.retrying(func, mock_env, participant=participant) == "ok"

        assert participant.rollbacks == [exc]
        assert participant.retries == [exc]

    def test_integrity_error_rolls_back_but_never_retries(
        self, mod, mock_env, participant
    ):
        from odoo.exceptions import ValidationError

        exc = _FakeIntegrityError(table_name="some_table")
        matching_model = MagicMock()
        matching_model._name = "some.model"
        matching_model._table = "some_table"
        matching_model._sql_error_to_message.return_value = "Unique constraint"
        mock_env.registry.models_by_table = {"some_table": matching_model}
        mock_env.__getitem__ = MagicMock(return_value=matching_model)

        def func():
            raise exc

        with pytest.raises(ValidationError):
            mod.retrying(func, mock_env, participant=participant)

        assert participant.rollbacks == [exc]
        assert participant.retries == []

    def test_a_non_retryable_operational_error_rolls_back_but_never_retries(
        self, mod, mock_env, participant
    ):
        exc = psycopg.OperationalError("connection reset")
        exc.sqlstate = None

        def func():
            raise exc

        with pytest.raises(psycopg.OperationalError):
            mod.retrying(func, mock_env, participant=participant)

        assert participant.rollbacks == [exc]
        assert participant.retries == []

    def test_exhausting_the_retries_fires_one_fewer_retry_than_rollback(
        self, mod, mock_env, tx, participant
    ):
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"

        def func():
            raise exc

        with (
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_backoff.get_delay.return_value = 0.0
            with pytest.raises(psycopg.errors.SerializationFailure):
                mod.retrying(func, mock_env, participant=participant)

        assert len(participant.rollbacks) == tx.MAX_TRIES_ON_CONCURRENCY_FAILURE
        assert len(participant.retries) == tx.MAX_TRIES_ON_CONCURRENCY_FAILURE - 1

    def test_no_participant_means_no_hooks_and_no_http_import(self, mod, tx, mock_env):
        exc = psycopg.errors.SerializationFailure()
        exc.sqlstate = "40001"
        calls = 0

        def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise exc
            return "ok"

        assert not hasattr(tx, "current_retry_participant")
        with (
            patch("odoo.service.transaction.time"),
            patch("odoo.service.transaction.backoff") as mock_backoff,
        ):
            mock_backoff.get_delay.return_value = 0.0
            assert mod.retrying(func, mock_env) == "ok"


class TestUncommittedWarningSuppression:
    def test_the_participant_can_suppress_the_warning(
        self, mod, tx, mock_env, participant
    ):
        participant.suppress = True
        mock_env.cr.closed = True
        with patch.object(tx._logger, "warning") as warn:
            mod.retrying(lambda: "done", mock_env, participant=participant)
        warn.assert_not_called()

    def test_otherwise_the_warning_is_emitted(self, mod, tx, mock_env, participant):
        participant.suppress = False
        mock_env.cr.closed = True
        with patch.object(tx._logger, "warning") as warn:
            mod.retrying(lambda: "done", mock_env, participant=participant)
        warn.assert_called_once()


@pytest.fixture
def owns_rpc_model_method(monkeypatch):
    monkeypatch.setattr(
        threading.current_thread(), "rpc_model_method", None, raising=False
    )


class TestExecuteCr:
    def _env(self, recs):
        env = MagicMock()
        env.get.return_value = recs
        return env

    def _run(self, mod, *, recs=None, retrying_returns="ok"):
        cr = MagicMock()
        env = self._env(MagicMock() if recs is None else recs)
        with (
            patch.object(mod.api, "Environment", return_value=env),
            patch.object(mod, "retrying", return_value=retrying_returns) as retry,
        ):
            result = mod.execute_cr(cr, 7, "res.partner", "read", [[1]], {})
        return result, cr, env, retry

    def test_cursor_is_reset_before_the_call(self, mod, owns_rpc_model_method):
        _result, cr, _env, _retry = self._run(mod)
        cr.reset.assert_called_once_with()

    def test_result_is_passed_through_force_lazy_values(
        self, mod, owns_rpc_model_method
    ):
        cr = MagicMock()
        env = self._env(MagicMock())
        sentinel = object()
        with (
            patch.object(mod.api, "Environment", return_value=env),
            patch.object(mod, "retrying", side_effect=lambda fn, *a: fn()),
            patch.object(mod, "call_kw", return_value="raw"),
            patch.object(mod, "_force_lazy_values", return_value=sentinel) as forced,
        ):
            out = mod.execute_cr(cr, 7, "res.partner", "read", [[1]], {})
        forced.assert_called_once_with("raw")
        assert out is sentinel, "execute_cr returned the unforced result"

    def test_a_real_lazy_in_the_result_is_materialised(
        self, mod, owns_rpc_model_method
    ):
        from odoo.tools import lazy

        produced = []

        def produce():
            produced.append(1)
            return 42

        cr = MagicMock()
        env = self._env(MagicMock())
        with (
            patch.object(mod.api, "Environment", return_value=env),
            patch.object(mod, "retrying", side_effect=lambda fn, *a: fn()),
            patch.object(mod, "call_kw", return_value={"total": lazy(produce)}),
        ):
            out = mod.execute_cr(cr, 7, "res.partner", "read", [[1]], {})
            assert produced == [1], (
                "the lazy was still unevaluated when execute_cr returned; it "
                "would materialise against a closed cursor"
            )
        assert out == {"total": 42}

    def test_unknown_model_raises_user_error(self, mod, owns_rpc_model_method):
        from odoo.exceptions import UserError

        cr = MagicMock()
        env = self._env(None)
        with (
            patch.object(mod.api, "Environment", return_value=env),
            patch.object(mod, "retrying") as retry,
        ):
            with pytest.raises(UserError, match="doesn't exist"):
                mod.execute_cr(cr, 7, "no.such.model", "read", [[1]], {})
        retry.assert_not_called()

    def test_the_call_is_routed_through_retrying(self, mod, owns_rpc_model_method):
        _result, _cr, env, retry = self._run(mod)
        retry.assert_called_once()
        thunk, passed_env, participant = retry.call_args.args
        assert participant is None, "the RPC path runs with no retry participant"
        assert passed_env is env
        with patch.object(mod, "call_kw", return_value="ok") as called:
            assert thunk() == "ok"
        assert called.call_args.args[1:] == ("read", [[1]], {})

    def test_thread_is_labelled_with_model_and_method(self, mod, owns_rpc_model_method):
        self._run(mod)
        assert threading.current_thread().rpc_model_method == "res.partner.read"

    def test_environment_is_built_under_the_caller_uid(
        self, mod, owns_rpc_model_method
    ):
        cr = MagicMock()
        env = self._env(MagicMock())
        with (
            patch.object(mod.api, "Environment", return_value=env) as environment,
            patch.object(mod, "retrying", return_value="ok"),
        ):
            mod.execute_cr(cr, 7, "res.partner", "read", [[1]], {})
        environment.assert_called_once_with(cr, 7, {})
        assert env.transaction.default_env is env


class TestCallKw:
    def _model(self):
        model = MagicMock()
        model._name = "res.partner"
        model.with_context.return_value = model
        return model

    @staticmethod
    def _resolver(expected_name, method):
        def _get(_model, name):
            assert name == expected_name, (
                f"call_kw resolved {name!r} for a call to {expected_name!r}; "
                "the access-control gate is checking the wrong method"
            )
            return method

        return _get

    def test_create_with_dict_vals_returns_scalar_id(self, mod):
        method = MagicMock(__name__="create", _api_model=True)
        method.return_value = MagicMock(id=42, ids=[42])
        with patch.object(mod, "get_public_method", self._resolver("create", method)):
            out = mod.call_kw(self._model(), "create", [{"name": "x"}], {})
        assert out == 42

    def test_create_with_list_vals_returns_ids_list(self, mod):
        method = MagicMock(__name__="create", _api_model=True)
        method.return_value = MagicMock(id=1, ids=[1, 2])
        with patch.object(mod, "get_public_method", self._resolver("create", method)):
            out = mod.call_kw(self._model(), "create", [[{"a": 1}, {"a": 2}]], {})
        assert out == [1, 2]

    def test_create_return_shape_reads_the_vals_the_caller_sent(self, mod):
        method = MagicMock(__name__="create", _api_model=True)
        method.return_value = MagicMock(id=42, ids=[42])
        model = self._model()
        with patch.object(mod, "get_public_method", return_value=method):
            out = mod.call_kw(model, "create", [{"name": "x"}, {"extra": "arg"}], {})
        assert out == 42

    def test_create_without_the_api_model_marker_names_the_cause(self, mod):
        from odoo.exceptions import AccessError

        method = MagicMock(__name__="create", _api_model=False)
        model = self._model()
        with patch.object(mod, "get_public_method", return_value=method):
            with pytest.raises(AccessError, match=r"api\.model_create_multi"):
                mod.call_kw(model, "create", [{"name": "x"}], {})
        method.assert_not_called()
        model.browse.assert_not_called()

    def test_recordset_result_is_reduced_to_ids(self, mod):
        rs = MagicMock(spec=mod.BaseModel)
        rs.ids = [7, 8]
        method = MagicMock(__name__="search", _api_model=False, return_value=rs)
        with patch.object(mod, "get_public_method", self._resolver("search", method)):
            out = mod.call_kw(self._model(), "search", [[1, 2]], {})
        assert out == [7, 8]

    def test_non_model_method_without_ids_raises_accesserror(self, mod):
        from odoo.exceptions import AccessError

        method = MagicMock(__name__="write")
        del method._api_model
        model = MagicMock()
        model._name = "res.partner"
        with patch.object(mod, "get_public_method", self._resolver("write", method)):
            with pytest.raises(AccessError):
                mod.call_kw(model, "write", [], {})

    def test_ids_are_split_off_and_the_rest_stay_positional(self, mod):
        method = MagicMock(__name__="write", return_value=True)
        del method._api_model
        model = self._model()
        with patch.object(mod, "get_public_method", self._resolver("write", method)):
            mod.call_kw(model, "write", [[7, 8], {"name": "x"}, "extra"], {})
        model.browse.assert_called_once_with([7, 8])
        recs = model.browse.return_value.with_context.return_value
        method.assert_called_once_with(recs, {"name": "x"}, "extra")

    def test_the_caller_context_reaches_the_recordset(self, mod):
        method = MagicMock(__name__="read", return_value=[])
        del method._api_model
        model = self._model()
        ctx = {"lang": "es_MX", "tz": "America/Mexico_City"}
        with patch.object(mod, "get_public_method", self._resolver("read", method)):
            mod.call_kw(model, "read", [[1]], {"context": ctx})
        model.browse.return_value.with_context.assert_called_once_with(ctx)

    def test_a_missing_context_becomes_an_empty_dict_not_none(self, mod):
        method = MagicMock(__name__="read", return_value=[])
        del method._api_model
        model = self._model()
        with patch.object(mod, "get_public_method", self._resolver("read", method)):
            mod.call_kw(model, "read", [[1]], {})
        model.browse.return_value.with_context.assert_called_once_with({})

    def test_context_is_not_forwarded_as_a_keyword_argument(self, mod):
        method = MagicMock(__name__="read", return_value=[])
        del method._api_model
        model = self._model()
        with patch.object(mod, "get_public_method", self._resolver("read", method)):
            mod.call_kw(model, "read", [[1]], {"context": {"lang": "en"}, "load": "_"})
        assert "context" not in method.call_args.kwargs
        assert method.call_args.kwargs == {"load": "_"}

    def test_create_without_vals_raises_accesserror_before_calling(self, mod):
        from odoo.exceptions import AccessError

        method = MagicMock(__name__="create", _api_model=True)
        with patch.object(mod, "get_public_method", self._resolver("create", method)):
            with pytest.raises(AccessError, match="requires a vals dict"):
                mod.call_kw(self._model(), "create", [], {})
        method.assert_not_called()


class TestDispatchValidation:
    def test_unknown_verb_raises_attributeerror(self, mod):
        with pytest.raises(AttributeError):
            mod.dispatch("not_a_verb", ["db", 1, "pw", "res.partner", "read"])

    def test_too_few_params_raises_typeerror(self, mod):
        with pytest.raises(TypeError):
            mod.dispatch("execute", ["db", 1, "pw"])

    def test_unexposed_database_refused_before_registry(self, mod):
        from odoo.exceptions import AccessDenied
        from odoo.tools import config

        def _must_not_run(*a, **kw):
            raise AssertionError("Registry must not be built for an unexposed db")

        with (
            config.patch(db_name=["served_db"]),
            patch.object(mod, "Registry", side_effect=_must_not_run),
        ):
            with pytest.raises(AccessDenied):
                mod.dispatch(
                    "execute", ["other_db", 1, "pw", "res.partner", "read", [1]]
                )

    @pytest.mark.parametrize("db", ["postgres", "template1"])
    def test_system_database_refused_before_registry(self, mod, db):
        from odoo.exceptions import AccessDenied

        def _must_not_run(*a, **kw):
            raise AssertionError("Registry must not be built for a system db")

        with patch.object(mod, "Registry", side_effect=_must_not_run):
            with pytest.raises(AccessDenied):
                mod.dispatch("execute", [db, 1, "pw", "res.partner", "read", [1]])

    def test_exposed_database_still_reaches_the_registry(self, mod):
        from odoo.tools import config

        for options in ({"db_name": []}, {"db_name": ["served_db"]}):
            with (
                config.patch(**options),
                patch.object(mod, "Registry", side_effect=RuntimeError("reached")),
            ):
                with pytest.raises(RuntimeError, match="reached"):
                    mod.dispatch(
                        "execute", ["served_db", 1, "pw", "res.partner", "read", [1]]
                    )

    def test_absent_database_answers_access_denied(self, mod):
        from odoo.exceptions import AccessDenied

        with patch.object(
            mod,
            "Registry",
            side_effect=psycopg.errors.InvalidCatalogName('database "x" ...'),
        ):
            with pytest.raises(AccessDenied):
                mod.dispatch(
                    "execute", ["gone_db", 1, "pw", "res.partner", "read", [1]]
                )

    @pytest.mark.parametrize(
        ("exc_factory", "match"),
        [
            (lambda: psycopg.OperationalError("PG is down"), "PG is down"),
            (
                lambda: __import__("odoo.db", fromlist=["PoolError"]).PoolError(
                    "saturated"
                ),
                "saturated",
            ),
        ],
    )
    def test_real_outages_are_not_masked_as_access_denied(
        self, mod, exc_factory, match
    ):
        with patch.object(mod, "Registry", side_effect=exc_factory()):
            with pytest.raises(Exception, match=match) as excinfo:
                mod.dispatch("execute", ["a_db", 1, "pw", "res.partner", "read", [1]])
        from odoo.exceptions import AccessDenied

        assert not isinstance(excinfo.value, AccessDenied)

    def test_bool_uid_rejected_before_registry(self, mod):
        with pytest.raises(TypeError):
            mod.dispatch("execute", ["db", True, "pw", "res.partner", "read", [1]])

    def test_float_uid_rejected_before_registry(self, mod):
        with pytest.raises(TypeError):
            mod.dispatch("execute", ["db", 1.9, "pw", "res.partner", "read", [1]])

    def test_empty_password_raises_accessdenied(self, mod):
        from odoo.exceptions import AccessDenied

        with pytest.raises(AccessDenied):
            mod.dispatch("execute", ["db", 1, "", "res.partner", "read", [1]])

    def test_exactly_five_params_is_enough_for_execute(self, mod):
        with patch.object(mod, "Registry", side_effect=RuntimeError("past the guard")):
            with pytest.raises(RuntimeError, match="past the guard"):
                mod.dispatch("execute", ["db", 1, "pw", "res.partner", "read"])

    def test_four_params_is_still_too_few(self, mod):
        with pytest.raises(TypeError, match="at least 5"):
            mod.dispatch("execute", ["db", 1, "pw", "res.partner"])


class TestDispatchExecuteVersusExecuteKw:
    @staticmethod
    def _driven(mod, verb, params):
        seen = {}

        def fake_execute_cr(cr, uid, model, method, args, kw):
            seen.update(uid=uid, model=model, method=method, args=args, kw=kw)
            return "ok"

        registry = MagicMock()
        cursor = fake_pg_cursor()
        registry.check_signaling.return_value = registry
        registry.cursor.return_value = cursor

        with (
            patch.object(mod, "Registry", return_value=registry),
            patch.object(mod, "execute_cr", fake_execute_cr),
            patch("odoo.api.Environment"),
        ):
            result = mod.dispatch(verb, params)
        return result, seen

    def test_execute_passes_its_arguments_through_with_no_kwargs(self, mod):
        _result, seen = self._driven(
            mod, "execute", ["db", 1, "pw", "res.partner", "read", [7], ["name"]]
        )
        assert seen["args"] == [[7], ["name"]], (
            "execute must forward every trailing param as positional args"
        )
        assert seen["kw"] == {}, "execute takes no keyword arguments"

    def test_execute_kw_unpacks_args_and_kw(self, mod):
        _result, seen = self._driven(
            mod,
            "execute_kw",
            ["db", 1, "pw", "res.partner", "read", [7], {"context": {"lang": "en"}}],
        )
        assert seen["args"] == [7]
        assert seen["kw"] == {"context": {"lang": "en"}}

    def test_execute_kw_defaults_missing_kw_to_an_empty_dict(self, mod):
        _result, seen = self._driven(
            mod, "execute_kw", ["db", 1, "pw", "res.partner", "read", [7]]
        )
        assert seen["args"] == [7]
        assert seen["kw"] == {}

    def test_execute_kw_treats_an_explicit_none_kw_as_empty(self, mod):
        _result, seen = self._driven(
            mod, "execute_kw", ["db", 1, "pw", "res.partner", "read", [7], None]
        )
        assert seen["kw"] == {}

    def test_the_credentials_are_checked_before_the_call(self, mod):
        from odoo.exceptions import AccessDenied

        registry = MagicMock()
        cursor = fake_pg_cursor()
        registry.check_signaling.return_value = registry
        registry.cursor.return_value = cursor

        users = MagicMock()
        users._check_uid_passwd.side_effect = AccessDenied
        env = MagicMock()
        env.__getitem__ = MagicMock(return_value=users)

        with (
            patch.object(mod, "Registry", return_value=registry),
            patch.object(mod, "execute_cr") as execute_cr,
            patch("odoo.api.Environment", return_value=env),
        ):
            with pytest.raises(AccessDenied):
                mod.dispatch("execute", ["db", 1, "bad", "res.partner", "read"])
        execute_cr.assert_not_called()


class TestDispatchArgShape:
    def test_execute_kw_bad_arg_shape_raises_typeerror(self, mod):
        with patch.object(mod, "Registry") as reg:
            reg.return_value.check_signaling.return_value = reg.return_value
            with pytest.raises(TypeError):
                mod.dispatch(
                    "execute_kw",
                    ["db", 1, "pw", "res.partner", "read", [1], {}, "extra"],
                )


class TestABadMethodNameIsAClientErrorNotAServerFault:
    """`get_public_method`'s six AccessErrors are logged quietly; this was not.

    `http.application._log_request_exception` classifies: `AccessError` and
    `UserError` become warnings, anything else becomes "Exception during
    request handling" at ERROR with a traceback. A plain `AttributeError` fell
    into the catch-all, so every typo'd method name from any authenticated
    client wrote twenty frames of Odoo's own dispatch stack to the log.
    Measured over eight refused RPC calls against a live server: six quiet,
    one AccessDenied at WARNING, and this one alone reported as a fault.

    The exception type is deliberately unchanged -- clients see the same
    `builtins.AttributeError` -- and `loglevel` is the seam that method checks
    before anything else.
    """

    def test_the_missing_method_error_carries_a_client_level(self, mod) -> None:
        import logging as _logging

        with patch.object(mod, "BaseModel", _FakeBaseModel):
            with pytest.raises(AttributeError) as caught:
                mod.get_public_method(_FakeModel(), "missing_xyz")
        assert getattr(caught.value, "loglevel", None) == _logging.WARNING, (
            "a bad RPC method name is still reported as a server fault"
        )

    def test_it_is_the_attribute_the_http_layer_reads(self, caplog) -> None:
        """Pin the seam, so renaming it on either side cannot pass silently."""
        import logging as _logging

        from odoo.http import application

        error = AttributeError("The method 'res.users.nope' does not exist")
        error.loglevel = _logging.WARNING
        with caplog.at_level(_logging.DEBUG, logger=application._logger.name):
            application.Application._log_request_exception(MagicMock(), error)
        (record,) = [r for r in caplog.records if r.name == application._logger.name]
        assert record.levelno == _logging.WARNING
        assert "res.users.nope" in record.getMessage()
