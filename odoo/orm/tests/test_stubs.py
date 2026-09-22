import os
import subprocess
import sys
from itertools import count
from pathlib import Path

import pytest

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.orm.stubs import class_name, render, render_registry

_MOD = "test_stubs"


class Author(models.Model):
    _name = "stub.author"
    _module = _MOD
    _description = "author"

    name = fields.Char()
    born = fields.Date()
    book_ids = fields.One2many("stub.book", "author_id")


class Book(models.Model):
    _name = "stub.book"
    _module = _MOD
    _description = "book"

    title = fields.Char(required=True)

    def action_publish(self, when, *, notify=False):
        return when

    @staticmethod
    def normalize_title(title):
        return title.strip()

    @classmethod
    def is_book_class(cls):
        return True

    @api.model
    def _from_title(self, title):
        return self.search([("title", "=", title)], limit=1)

    pages = fields.Integer()
    price = fields.Float()
    author_id = fields.Many2one("stub.author")
    tag_ids = fields.Many2many("stub.tag")


class Tag(models.Model):
    _name = "stub.tag"
    _module = _MOD
    _description = "tag"

    name = fields.Char()


def test_class_name_camel_cases_dots_and_underscores():
    assert class_name("res.partner") == "ResPartner"
    assert class_name("ir.model.fields") == "IrModelFields"
    assert class_name("account_move.line") == "AccountMoveLine"
    assert class_name("2d.shape") == "Model2dShape"


def test_render_types_every_field_and_relations_to_the_comodel_class():
    with model_test_env(Author, Book, Tag) as env:
        source = render_registry(env.registry)
    assert "class StubBook(BaseModel):" in source
    assert '    _name: Literal["stub.book"]' in source
    assert "    title: _F[str | Literal[False]]" in source
    assert "    pages: _F[int]" in source
    assert "    price: _F[float]" in source
    assert "    author_id: _F[StubAuthor]" in source
    assert "    tag_ids: _F[StubTag]" in source
    assert "    book_ids: _F[StubBook]" in source
    assert "    born: _F[datetime.date | Literal[False]]" in source
    assert (
        "    def action_publish(self, when: Any, *, notify: Any = ...) -> Any: ..."
        in source
    )
    assert "    def _from_title(self, title: Any) -> Any: ..." in source
    assert (
        "    @staticmethod\n    def normalize_title(title: Any) -> Any: ..." in source
    )
    assert "    @classmethod\n    def is_book_class(cls) -> Any: ..." in source
    assert "    id: _F[int]" in source
    assert (
        '    def __getitem__(self, model_name: Literal["stub.book"]) -> StubBook: ...'
        in source
    )
    compile(source, "odoo_registry_stubs.pyi", "exec")


def test_render_refuses_two_models_stubbing_as_one_class():
    with pytest.raises(ValueError, match="both stub as"):
        render([("a.b", {}), ("a_b", {})])


def test_render_marks_a_field_that_shadows_a_base_method():
    source = render([("s.m", {"count": fields.Integer()})], reserved={"count"})
    assert "    count: _F[int]  # type: ignore[assignment]" in source


def test_render_skips_a_field_named_like_a_keyword():
    source = render([("k.w", {"class": fields.Char(), "ok": fields.Char()})])
    assert "    ok: _F[" in source
    assert "    class: " not in source


def _run_mypy(tmp_path, source, client_source, *, check_stub=False):
    root = Path(__file__).resolve().parents[3]
    stub = tmp_path / "odoo_registry_stubs.pyi"
    if source is not None:
        stub.write_text(source)
    config = tmp_path / "mypy.ini"
    config.write_text(
        "[mypy]\npython_version = 3.14\nfollow_imports = silent\n"
        "ignore_missing_imports = True\n"
        f"cache_dir = {tmp_path / 'mypy-cache'}\n"
        f"plugins = {root / 'mypy_registry_plugin.py'}\n"
    )
    client = tmp_path / "client.py"
    client.write_text(client_source)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--no-incremental",
            "--config-file",
            str(config),
            str(client),
            *([str(stub)] if check_stub else []),
        ],
        cwd=root,
        env={**os.environ, "MYPYPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_mypy_accepts_registry_methods_and_rejects_unknown_models(tmp_path):
    with model_test_env(Author, Book, Tag) as env:
        source = render_registry(env.registry)
    result = _run_mypy(
        tmp_path,
        source,
        "from odoo.api import Environment\n\n"
        "def valid(env: Environment, model_name: str) -> None:\n"
        "    env['stub.book'].action_publish('today', notify=True)\n"
        "    env['stub.book'].normalize_title(' title ')\n"
        "    env['stub.book'].is_book_class()\n"
        "    env['stub.book'].author_id.book_ids.action_publish('today')\n"
        "    env[model_name].search([])\n\n"
        "def invalid(env: Environment) -> None:\n"
        "    env['stub.bok'].search([])\n"
        "    env['stub.book'].action_publsih('today')\n",
    )
    assert result.returncode == 1, result.stdout + result.stderr
    errors = [line for line in result.stdout.splitlines() if ": error:" in line]
    assert len(errors) == 2, result.stdout + result.stderr
    assert "Model 'stub.bok' is absent" in errors[0]
    assert 'has no attribute "action_publsih"' in errors[1]


@pytest.mark.parametrize("source", [None, render([])], ids=["missing", "empty"])
def test_mypy_refuses_missing_or_empty_registry_types(tmp_path, source):
    result = _run_mypy(
        tmp_path,
        source,
        "from odoo.api import Environment\n"
        "def lookup(env: Environment) -> None:\n"
        "    env['stub.book'].search([])\n",
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "No generated registry model types were loaded" in result.stdout


def test_generated_model_names_do_not_shadow_stub_infrastructure(tmp_path):
    names = [
        "environment",
        "base.model",
        "any",
        "literal",
        "generic",
        "type.var",
        "none",
        "true",
        "false",
    ]
    source = render([(name, {}) for name in names])
    client = "from odoo.api import Environment\n"
    client += "def lookup(env: Environment) -> None:\n"
    client += "".join(f"    env[{name!r}].search([])\n" for name in names)
    result = _run_mypy(tmp_path, source, client, check_stub=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_an_empty_registry_generates_a_valid_stub(tmp_path):
    result = _run_mypy(tmp_path, render([]), "", check_stub=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_mypy_daemon_sees_regenerated_models(tmp_path):
    root = Path(__file__).resolve().parents[3]
    stub = tmp_path / "odoo_registry_stubs.pyi"
    client = tmp_path / "client.py"
    config = tmp_path / "mypy.ini"
    config.write_text(
        "[mypy]\npython_version = 3.14\nfollow_imports = normal\n"
        "ignore_missing_imports = True\n"
        f"cache_dir = {tmp_path / 'mypy-cache'}\n"
        f"plugins = {root / 'mypy_registry_plugin.py'}\n"
        "[mypy-odoo.*]\nignore_errors = True\n"
    )
    command = [
        sys.executable,
        "-m",
        "mypy.dmypy",
        "--status-file",
        str(tmp_path / "status.json"),
    ]

    def run(*args):
        return subprocess.run(
            [*command, *args],
            cwd=root,
            env={**os.environ, "MYPYPATH": str(tmp_path)},
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    revisions = count(1)

    def snapshot(names, lookup):
        revision = next(revisions)
        stub.write_text(render([(name, {}) for name in names]))
        # mypy's watcher rounds mtimes to seconds for same-sized files.
        os.utime(stub, (revision, revision))
        source = (
            "from odoo.api import Environment\n"
            "def lookup(env: Environment) -> None:\n"
            f"    env[{lookup!r}].search([])\n"
        )
        if not client.exists() or client.read_text() != source:
            client.write_text(source)
            os.utime(client, (revision, revision))

    try:
        snapshot(["stub.book"], "stub.book")
        initial = run("run", "--", "--config-file", str(config), str(client))
        assert initial.returncode == 0, initial.stdout + initial.stderr
        snapshot(["stub.book", "stub.author"], "stub.author")
        added = run("recheck")
        assert added.returncode == 0, added.stdout + added.stderr
        snapshot(["stub.book"], "stub.author")
        removed = run("recheck")
        assert removed.returncode == 1, removed.stdout + removed.stderr
        assert "Model 'stub.author' is absent" in removed.stdout
        snapshot(["stub.author"], "stub.author")
        restored = run("recheck")
        assert restored.returncode == 0, restored.stdout + restored.stderr
        snapshot(["stub_author"], "stub.author")
        renamed = run("recheck")
        assert renamed.returncode == 1, renamed.stdout + renamed.stderr
        assert "Model 'stub.author' is absent" in renamed.stdout
        stub.unlink()
        missing = run("recheck")
        assert missing.returncode == 1, missing.stdout + missing.stderr
        assert "No generated registry model types were loaded" in missing.stdout
    finally:
        stopped = run("stop")
        assert stopped.returncode == 0, stopped.stdout + stopped.stderr


def test_generated_methods_preserve_binding_defaults_and_awaitability(tmp_path):
    class Signatures:
        @staticmethod
        def optional(value=None, /, *, self=None, cls=False):
            return value, self, cls

        def configure(self, *, cls=False):
            return cls

        async def fetch_value(self, value):
            return value

    source = render(
        [("signature.probe", {})], classes_by_model={"signature.probe": Signatures}
    )
    result = _run_mypy(
        tmp_path,
        source,
        "from odoo.api import Environment\n"
        "async def valid(env: Environment) -> None:\n"
        "    env['signature.probe'].optional()\n"
        "    env['signature.probe'].configure()\n"
        "    await env['signature.probe'].fetch_value(1)\n"
        "def invalid(env: Environment) -> None:\n"
        "    env['signature.probe'].fetch_value(1)\n",
        check_stub=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    errors = [line for line in result.stdout.splitlines() if ": error:" in line]
    assert len(errors) == 1, result.stdout + result.stderr
    assert "unused-coroutine" in errors[0]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
