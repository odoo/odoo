from unittest.mock import MagicMock, patch

import pytest

from .conftest import fake_pg_cursor


@pytest.fixture(scope="module")
def common_mod():
    import odoo.service.common as mod

    return mod


class TestDispatchAllowlist:
    def test_allowlist_contains_expected_public_methods(self, common_mod):
        assert set(common_mod._DISPATCH) == {"login", "authenticate", "version"}

    def test_unknown_method_raises(self, common_mod):
        with pytest.raises(AttributeError, match="Method not found"):
            common_mod.dispatch("not_a_real_method", [])

    def test_accidental_exp_helper_is_not_reachable(self, common_mod):
        def exp_accidental_debug_helper():
            return "this should never be reachable via RPC"

        with patch.object(
            common_mod,
            "exp_accidental_debug_helper",
            exp_accidental_debug_helper,
            create=True,
        ):
            with pytest.raises(AttributeError, match="Method not found"):
                common_mod.dispatch("accidental_debug_helper", [])

    def test_version_dispatch_matches_direct_call(self, common_mod):
        direct = common_mod.exp_version()
        via_dispatch = common_mod.dispatch("version", [])
        assert direct == via_dispatch

    def test_allowlist_values_are_callable(self, common_mod):
        for name, handler in common_mod._DISPATCH.items():
            assert callable(handler), f"{name!r} maps to non-callable {handler!r}"

    def test_login_is_a_thin_wrapper_over_authenticate(self, common_mod):
        with patch.object(common_mod, "exp_authenticate", return_value=42) as mock:
            result = common_mod.exp_login("mydb", "alice", "pw")
        mock.assert_called_once_with("mydb", "alice", "pw", None)
        assert result == 42


class TestVersionPayload:
    @pytest.mark.parametrize(
        "key", ["server_version", "server_version_info", "server_serie"]
    )
    def test_version_keys_are_published(self, common_mod, key):
        assert key in common_mod.exp_version()

    def test_protocol_version_is_pinned(self, common_mod):
        assert common_mod.exp_version()["protocol_version"] == 1

    def test_version_follows_a_late_patch_of_odoo_release(self, common_mod):
        import odoo.release

        with (
            patch.object(odoo.release, "version", "19.0-PATCHED+e"),
            patch.object(odoo.release, "version_info", (19, 0, 0, "final", 0, "e")),
        ):
            payload = common_mod.exp_version()
        assert payload["server_version"] == "19.0-PATCHED+e"
        assert payload["server_version_info"] == (19, 0, 0, "final", 0, "e")

        assert common_mod.exp_version()["server_version"] == odoo.release.version

    def test_each_version_payload_is_a_fresh_dict(self, common_mod):
        payload = common_mod.exp_version()
        payload["server_version"] = "tampered"
        assert common_mod.exp_version()["server_version"] != "tampered"


class TestExpAuthenticateExceptionAbsorption:
    def test_pool_error_returns_false_not_raise(self, common_mod):
        from odoo.db import PoolError

        with patch.object(
            common_mod, "Registry", side_effect=PoolError("pool exhausted")
        ) as registry:
            assert common_mod.exp_authenticate("any_db", "u", "p", None) is False
        registry.assert_called_once_with("any_db")

    def test_psycopg_operational_error_still_returns_false(self, common_mod):
        import psycopg

        with patch.object(
            common_mod, "Registry", side_effect=psycopg.OperationalError("PG down")
        ):
            assert common_mod.exp_authenticate("any_db", "u", "p", None) is False

    def test_invalid_catalog_name_returns_false_not_raise(self, common_mod):
        import psycopg

        assert not issubclass(
            psycopg.errors.InvalidCatalogName, psycopg.OperationalError
        ), "premise of this test: InvalidCatalogName is not an OperationalError"
        with patch.object(
            common_mod,
            "Registry",
            side_effect=psycopg.errors.InvalidCatalogName(
                'database "x" does not exist'
            ),
        ):
            assert common_mod.exp_authenticate("no_such_db", "u", "p", None) is False

    @pytest.mark.parametrize(
        "exc_name", ["InsufficientPrivilege", "InvalidPassword", "TooManyConnections"]
    )
    def test_any_psycopg_error_returns_false(self, common_mod, exc_name):
        import psycopg

        with patch.object(
            common_mod,
            "Registry",
            side_effect=getattr(psycopg.errors, exc_name)("nope"),
        ):
            assert common_mod.exp_authenticate("any_db", "u", "p", None) is False

    def test_unexpected_db_error_is_logged_loudly_even_though_answer_is_false(
        self, common_mod, caplog
    ):
        import logging

        import psycopg

        with caplog.at_level(logging.DEBUG, logger="odoo.service.common"):
            with patch.object(
                common_mod,
                "Registry",
                side_effect=psycopg.errors.UndefinedTable(
                    "relation ... does not exist"
                ),
            ):
                assert common_mod.exp_authenticate("some_db", "u", "p", None) is False
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warnings, "an unexpected database error must not vanish at DEBUG"
        assert "unexpected database error" in warnings[0].getMessage()

    @pytest.mark.parametrize(
        "exc_factory",
        [
            lambda: __import__("psycopg").errors.InvalidCatalogName("no such db"),
            lambda: __import__("psycopg").OperationalError("PG down"),
        ],
    )
    def test_routine_connect_failures_stay_quiet(self, common_mod, caplog, exc_factory):
        import logging

        with caplog.at_level(logging.DEBUG, logger="odoo.service.common"):
            with patch.object(common_mod, "Registry", side_effect=exc_factory()):
                assert common_mod.exp_authenticate("any_db", "u", "p", None) is False
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]

    def test_unrelated_keyerror_propagates(self, common_mod):
        with patch.object(
            common_mod, "Registry", side_effect=KeyError("missing module")
        ):
            with pytest.raises(KeyError, match="missing module"):
                common_mod.exp_authenticate("any_db", "u", "p", None)

    def test_runtime_error_still_propagates(self, common_mod):
        with patch.object(
            common_mod, "Registry", side_effect=RuntimeError("registry boom")
        ):
            with pytest.raises(RuntimeError, match="registry boom"):
                common_mod.exp_authenticate("any_db", "u", "p", None)


class TestExpAuthenticateNotAnOdooDatabase:
    def test_missing_res_users_model_returns_false(self, common_mod):
        class _NotOdooRegistry:
            models = {"ir.model": object()}

            def cursor(self, *args, **kwargs):  # pragma: no cover - must not run
                raise AssertionError(
                    "cursor() must not be opened once res.users is known absent"
                )

        with patch.object(common_mod, "Registry", return_value=_NotOdooRegistry()):
            assert (
                common_mod.exp_authenticate("bare_db", "admin", "admin", None) is False
            )


class TestExpAuthenticateNeverServableNames:
    @pytest.mark.parametrize("db", ["postgres", "template0", "template1"])
    def test_system_dbs_refused_without_connecting(self, common_mod, db):
        def _must_not_run(*args, **kwargs):  # pragma: no cover - must not run
            raise AssertionError(f"Registry({db!r}) must not be built")

        with patch.object(common_mod, "Registry", side_effect=_must_not_run):
            assert common_mod.exp_authenticate(db, "admin", "admin", None) is False

    def test_unlisted_database_refused_when_database_option_is_set(self, common_mod):
        from odoo.tools import config

        def _must_not_run(*a, **kw):  # pragma: no cover - must not run
            raise AssertionError("Registry must not be built for an unlisted db")

        with (
            config.patch(db_name=["served_db"]),
            patch.object(common_mod, "Registry", side_effect=_must_not_run),
        ):
            assert common_mod.exp_authenticate("other_db", "a", "b", None) is False

    def test_listed_database_still_reaches_the_registry(self, common_mod):
        from odoo.tools import config

        for options in ({"db_name": []}, {"db_name": ["served_db"]}):
            with (
                config.patch(**options),
                patch.object(
                    common_mod, "Registry", side_effect=RuntimeError("reached")
                ),
            ):
                with pytest.raises(RuntimeError, match="reached"):
                    common_mod.exp_authenticate("served_db", "a", "b", None)

    def test_a_host_dbfilter_is_not_applied(self, common_mod):
        """`dispatch_rpc` runs with no request host, so `^%h$` would refuse
        every RPC login on a virtual-host deployment; an RPC caller names its
        database explicitly."""
        from odoo.service import _dispatch
        from odoo.tools import config

        _dispatch._compile_static_dbfilter.cache_clear()
        with (
            config.patch(dbfilter="^%h$", db_name=[]),
            patch.object(common_mod, "Registry", side_effect=RuntimeError("reached")),
        ):
            with pytest.raises(RuntimeError, match="reached"):
                common_mod.exp_authenticate("any_db", "a", "b", None)

    def test_a_static_dbfilter_scopes_rpc_like_it_scopes_cron(self, common_mod):
        from odoo.service import _dispatch
        from odoo.tools import config

        _dispatch._compile_static_dbfilter.cache_clear()

        def _must_not_run(*a, **kw):  # pragma: no cover - must not run
            raise AssertionError("Registry must not be built for a filtered-out db")

        with (
            config.patch(dbfilter="^served_", db_name=[]),
            patch.object(common_mod, "Registry", side_effect=_must_not_run),
        ):
            assert common_mod.exp_authenticate("other_db", "a", "b", None) is False
        with (
            config.patch(dbfilter="^served_", db_name=[]),
            patch.object(common_mod, "Registry", side_effect=RuntimeError("reached")),
        ):
            with pytest.raises(RuntimeError, match="reached"):
                common_mod.exp_authenticate("served_db", "a", "b", None)

    def test_configured_template_refused_without_connecting(self, common_mod):
        from odoo.tools import config

        def _must_not_run(*args, **kwargs):  # pragma: no cover - must not run
            raise AssertionError("Registry(db_template) must not be built")

        with (
            config.patch(db_template="tpl_custom"),
            patch.object(common_mod, "Registry", side_effect=_must_not_run),
        ):
            assert common_mod.exp_authenticate("tpl_custom", "a", "b", None) is False


class TestExpAuthenticateArgumentTypes:
    @pytest.mark.parametrize("db", [None, 42, b"bytes", ["mydb"], {"db": 1}, ""])
    def test_non_string_or_empty_db_returns_false(self, common_mod, db):
        def _must_not_run(*a, **kw):  # pragma: no cover - must not run
            raise AssertionError(f"Registry({db!r}) must not be built")

        with patch.object(common_mod, "Registry", side_effect=_must_not_run):
            assert common_mod.exp_authenticate(db, "u", "p", None) is False

    @pytest.mark.parametrize(
        ("login", "password"), [(None, "p"), ("u", None), (42, "p"), ("u", ["p"])]
    )
    def test_non_string_credentials_return_false(self, common_mod, login, password):
        def _must_not_run(*a, **kw):  # pragma: no cover - must not run
            raise AssertionError("Registry must not be built for non-str credentials")

        with patch.object(common_mod, "Registry", side_effect=_must_not_run):
            assert common_mod.exp_authenticate("db", login, password, None) is False

    @pytest.mark.parametrize("bad_env", [42, "string", ["list"], (1, 2)])
    def test_non_dict_user_agent_env_returns_false(self, common_mod, bad_env):
        def _must_not_run(*a, **kw):  # pragma: no cover - must not run
            raise AssertionError("Registry must not be built for a non-dict env")

        with patch.object(common_mod, "Registry", side_effect=_must_not_run):
            assert common_mod.exp_authenticate("db", "u", "p", bad_env) is False

    def test_none_user_agent_env_is_still_accepted(self, common_mod):
        with patch.object(common_mod, "Registry", side_effect=RuntimeError("reached")):
            with pytest.raises(RuntimeError, match="reached"):
                common_mod.exp_authenticate("db", "u", "p", None)


class TestExpAuthenticateCredentialOutcome:
    @staticmethod
    def _registry(authenticate):
        cursor = fake_pg_cursor()
        users = MagicMock()
        users.authenticate = authenticate
        registry = MagicMock()
        registry.models = {"res.users": object()}
        registry.cursor.return_value = cursor
        return registry, users

    def test_valid_credentials_return_the_uid(self, common_mod):
        registry, users = self._registry(lambda credential, env: {"uid": 7})
        env = MagicMock()
        env.__getitem__ = MagicMock(return_value=users)
        with (
            patch.object(common_mod, "Registry", return_value=registry),
            patch("odoo.api.Environment", return_value=env),
        ):
            assert common_mod.exp_authenticate("db", "alice", "pw", None) == 7

    def test_the_credential_dict_is_a_password_login(self, common_mod):
        seen = {}

        def authenticate(credential, env):
            seen["credential"] = credential
            seen["env"] = env
            return {"uid": 1}

        registry, users = self._registry(authenticate)
        env = MagicMock()
        env.__getitem__ = MagicMock(return_value=users)
        with (
            patch.object(common_mod, "Registry", return_value=registry),
            patch("odoo.api.Environment", return_value=env),
        ):
            common_mod.exp_authenticate("db", "alice", "s3cret", {"base_location": "x"})
        assert seen["credential"] == {
            "login": "alice",
            "password": "s3cret",
            "type": "password",
        }
        assert seen["env"]["interactive"] is False
        assert seen["env"]["base_location"] == "x"

    def test_wrong_password_returns_false_not_a_truthy_value(self, common_mod):
        from odoo.exceptions import AccessDenied

        def authenticate(credential, env):
            raise AccessDenied

        registry, users = self._registry(authenticate)
        env = MagicMock()
        env.__getitem__ = MagicMock(return_value=users)
        with (
            patch.object(common_mod, "Registry", return_value=registry),
            patch("odoo.api.Environment", return_value=env),
        ):
            result = common_mod.exp_authenticate("db", "alice", "wrong", None)
        assert result is False

    def test_an_unexpected_error_from_authenticate_still_propagates(self, common_mod):
        def authenticate(credential, env):
            raise RuntimeError("bug in the auth provider")

        registry, users = self._registry(authenticate)
        env = MagicMock()
        env.__getitem__ = MagicMock(return_value=users)
        with (
            patch.object(common_mod, "Registry", return_value=registry),
            patch("odoo.api.Environment", return_value=env),
        ):
            with pytest.raises(RuntimeError, match="bug in the auth provider"):
                common_mod.exp_authenticate("db", "alice", "pw", None)
