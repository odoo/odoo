import inspect
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest.mock import patch

from odoo.fields import Command
from odoo.models import Model
from odoo.tests import new_test_user, tagged

from .dummy_methods import DummyMethods
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.rpc.tools.cache import (
    ACCESS_CACHE_SEQUENCES,
    doc_cache_generation,
    stale_index_domain,
)
from odoo.addons.rpc.tools.registry import (
    _describing_docstring,
    describe_method,
    is_public_method,
    public_method_names,
    reflect_callable,
)


@tagged("-at_install", "post_install")
class TestDoc(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_demo.write(
            {
                "group_ids": [Command.link(cls.env.ref("rpc.group_allow_doc").id)],
            }
        )

    def test_doc_access(self):
        e = "This page is only accessible to Technical Documentation users."
        new_test_user(self.env, login="test_doc_access")
        self.authenticate("test_doc_access", "test_doc_access")
        for path in ("/doc", "/doc/index.json", "/doc/res.company.json"):
            with self.subTest(path=path):
                with self.assertLogs("odoo.http") as capture:
                    res = self.url_open(path)
                self.assertEqual(res.status_code, 403)
                self.assertIn(e, res.text)
                # dispatch-error logging lives in the odoo.http.application
                # submodule since the http package split
                self.assertEqual(capture.output, [f"WARNING:odoo.http.application:{e}"])

    def test_doc_web_client(self):
        self.authenticate("demo", "demo")
        res = self.url_open("/doc", allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "text/html; charset=utf-8")
        self.assertTrue(res.content, "There must be a rich web client")

    def test_doc_index_user(self):
        self.authenticate("demo", "demo")
        self._doc_index("doc")

    def test_doc_index_bearer(self):
        key = (
            self.env["res.users.apikeys"]
            .with_user(self.user_demo)
            ._generate(
                scope="rpc",
                name="test",
                expiration_date=datetime.now() + timedelta(days=0.5),
            )
        )
        self._doc_index("doc-bearer", headers={"Authorization": f"Bearer {key}"})

    def _doc_index(self, prefix, headers=None):
        res = self.url_open(
            f"/{prefix}/index.json", allow_redirects=False, headers=headers
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers.get("Content-Type"), "application/json; charset=utf-8"
        )

        json = res.json()
        self.assertEqual(set(json), {"models"})

        res_partner = next(
            (model for model in json["models"] if model["model"] == "res.partner"),
            None,
        )
        self.assertTrue(res_partner, "res.partner not found in json['models']")
        res_partner_fields = res_partner.pop("fields")
        res_partner_methods = res_partner.pop("methods")
        self.assertEqual(res_partner, {"name": "Contact", "model": "res.partner"})
        self.assertGreater(
            set(res_partner_methods), {"search", "open_commercial_entity"}
        )
        self.assertGreater(set(res_partner_fields), {"id", "create_uid", "lang", "tz"})

    def test_doc_model_user(self):
        self.authenticate("demo", "demo")
        self._doc_model("doc")

    def test_doc_model_bearer(self):
        key = (
            self.env["res.users.apikeys"]
            .with_user(self.user_demo)
            ._generate(
                scope="rpc",
                name="test",
                expiration_date=datetime.now() + timedelta(days=0.5),
            )
        )
        self._doc_model("doc-bearer", headers={"Authorization": f"Bearer {key}"})

    def _doc_model(self, prefix, headers=None):
        res = self.url_open(
            f"/{prefix}/res.partner.json", allow_redirects=False, headers=headers
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers.get("Content-Type"), "application/json; charset=utf-8"
        )

        json = res.json()
        fields = json.pop("fields", None)
        methods = json.pop("methods", None)
        self.maxDiff = None
        self.assertEqual(json.pop("model"), "res.partner")
        self.assertEqual(json.pop("name"), "Contact")
        self.assertEqual(set(json), {"doc"}, "no other top-level key is published")

        self.assertGreater(set(fields), {"id", "create_uid", "lang", "tz"})
        fields["id"].pop("ai", None)
        self.assertEqual(
            fields["id"],
            {
                "change_default": False,
                "company_dependent": False,
                "default_export_compatible": False,
                "depends": [],
                "exportable": True,
                "groupable": True,
                "manual": False,
                "module": None,
                "name": "id",
                "readonly": True,
                "required": False,
                "searchable": True,
                "sortable": True,
                "store": True,
                "string": "ID",
                "type": "integer",
            },
        )

        # `search` is pinned for its *shape*, not for the prose of a core
        # docstring: pinning the rendered docstring of an ORM method makes this
        # module's suite fail whenever the ORM edits a sentence, which is what
        # it did until this was rewritten.
        self.assertGreater(set(methods), {"search", "open_commercial_entity"})
        search = methods["search"]
        self.assertEqual(search["model"], "core")
        self.assertEqual(search["module"], "core")
        self.assertEqual(
            search["signature"],
            "(domain, offset=0, limit=None, order=None) -> list[int]",
            "Self must be published as what RPC really returns",
        )
        self.assertEqual(
            set(search["parameters"]), {"domain", "offset", "limit", "order"}
        )
        self.assertEqual(search["parameters"]["domain"]["annotation"], "DomainType")
        self.assertEqual(search["parameters"]["offset"]["default"], 0)
        self.assertEqual(search["api"], ["model", "readonly"])
        self.assertEqual(search["return"]["annotation"], "list[int]")

    def test_doc_model_publishes_no_unreflectable_method(self):
        """Every documented method reflects: none falls back to the stub.

        The stub exists for a callable nothing can introspect. It used to catch
        a whole class of ORM methods instead, because their annotations name
        types imported under ``if TYPE_CHECKING:``.
        """
        self.authenticate("demo", "demo")
        res = self.url_open("/doc/res.partner.json", allow_redirects=False)
        res.raise_for_status()
        stubbed = [
            name
            for name, method in res.json()["methods"].items()
            if method["signature"] == "(...)"
        ]
        self.assertEqual(stubbed, [], "these methods could not be reflected")

    def test_doc_model_signatures_keep_their_markers(self):
        """A published signature is one a reader can copy into a call."""
        self.authenticate("demo", "demo")
        res = self.url_open("/doc/res.partner.json", allow_redirects=False)
        res.raise_for_status()
        methods = res.json()["methods"]
        for name, method in methods.items():
            for param_name, param in method["parameters"].items():
                if param.get("kind") == "VAR_KEYWORD":
                    with self.subTest(method=name):
                        self.assertIn(f"**{param_name}", method["signature"])
                elif param.get("kind") == "VAR_POSITIONAL":
                    with self.subTest(method=name):
                        self.assertIn(f"*{param_name}", method["signature"])

    def test_doc_cache(self):
        self.authenticate("demo", "demo")

        # request the document first
        res = self.url_open("/doc/index.json", allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content, "We should have downloaded the document")

        # ensure the necessary is there to cache the document
        cache_control = sorted(res.headers.get("Cache-Control", "").split(", "))
        self.assertEqual(cache_control, ["no-cache", "private"])
        etag_demo = res.headers.get("ETag", "")
        self.assertTrue(etag_demo)

        # request the document again, this time using the cache
        res = self.url_open(
            "/doc/index.json",
            headers={"If-None-Match": etag_demo},
            allow_redirects=False,
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, HTTPStatus.NOT_MODIFIED)
        self.assertFalse(res.content, "We should not have downloaded the document")

        # request the document again, this time as admin
        self.authenticate("admin", "admin")
        res = self.url_open("/doc/index.json", allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200, "It must not be 304 - Not Modified")
        etag_admin = res.headers.get("ETag", "")
        self.assertTrue(etag_admin)
        self.assertNotEqual(etag_demo, etag_admin)

    def test_doc_model_etag_is_a_quoted_entity_tag(self):
        """RFC 9110 wants an ETag quoted; a cache in front of us may insist."""
        self.authenticate("demo", "demo")
        res = self.url_open("/doc/res.partner.json", allow_redirects=False)
        res.raise_for_status()
        etag = res.headers["ETag"]
        self.assertTrue(
            etag.startswith('"') and etag.endswith('"'),
            f"ETag is not a quoted-string: {etag}",
        )

    def test_doc_index_no_cache_refreshes_stale_attachment(self):
        """
        A client sending ``Cache-Control: no-cache`` must always get the
        freshly computed index, even if a (possibly stale) server-side
        attachment already exists under the same cache key.
        """
        self.authenticate("demo", "demo")

        # Prime the server-side attachment cache.
        res = self.url_open("/doc/index.json", allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)

        # Corrupt the cached attachment in place: this must never be served
        # again once a client asks for a non-cached response.
        index_attach = (
            self.env["ir.attachment"]
            .sudo()
            .search([("name", "like", "odoo-doc-index-%")], limit=1)
        )
        self.assertTrue(index_attach, "the /doc/index.json cache attachment must exist")
        index_attach.raw = b'{"models": [{"model": "__stale__"}]}'

        res = self.url_open(
            "/doc/index.json",
            headers={"Cache-Control": "no-cache"},
            allow_redirects=False,
        )
        res.raise_for_status()
        json = res.json()
        self.assertNotEqual(
            [m["model"] for m in json["models"]],
            ["__stale__"],
            "no-cache must bypass the stale server-side attachment cache",
        )

    def test_doc_index_is_cached_once_per_audience(self):
        """A second request reuses the attachment instead of storing another.

        Without that, every concurrent first request stores a duplicate row
        under the same name and nothing ever collects them.
        """
        Attachment = self.env["ir.attachment"].sudo()
        Attachment.search([("name", "like", "odoo-doc-index-%")]).unlink()
        self.authenticate("demo", "demo")
        for _ in range(3):
            self.url_open("/doc/index.json", allow_redirects=False).raise_for_status()
        names = Attachment.search([("name", "like", "odoo-doc-index-%")]).mapped("name")
        self.assertEqual(len(names), len(set(names)), f"duplicate cache rows: {names}")
        self.assertEqual(len(names), 1)

    def test_an_acl_write_invalidates_a_cache_group_the_key_tracks(self):
        """First half of the staleness guarantee: the ORM tells us.

        An ``ir.access`` write invalidates a cache group; if that group
        is not one the key is built from, a reader who has just lost access to
        a model keeps being served a document that still lists it.
        """
        self.env.registry.cache_invalidated.clear()
        self.env["ir.access"].sudo().search(
            [("model_id.model", "=", "res.country"), ("kind", "=", "permission")],
            limit=1,
        ).write({"active": False})
        self.env.flush_all()
        self.assertTrue(
            set(self.env.registry.cache_invalidated) & set(ACCESS_CACHE_SEQUENCES),
            f"an ACL write invalidated {sorted(self.env.registry.cache_invalidated)}, "
            f"none of which the /doc cache key tracks",
        )

    def test_the_cache_generation_moves_with_the_groups_it_tracks(self):
        """Second half: a moved sequence is a new generation.

        And `default` deliberately does not move it -- that group is bumped by
        ordinary ORM cache invalidation, which cannot change a line of the
        document but would rebuild a multi-megabyte index.
        """
        registry_sequence, sequences = self.env.registry.get_sequences(self.env.cr)
        baseline = doc_cache_generation(self.env)

        def frozen(moved):
            return lambda self_registry, cr: (registry_sequence, moved)

        for name in ACCESS_CACHE_SEQUENCES:
            moved = dict(sequences, **{name: sequences[name] + 1})
            with (
                self.subTest(sequence=name),
                patch.object(type(self.env.registry), "get_sequences", frozen(moved)),
            ):
                self.assertNotEqual(
                    doc_cache_generation(self.env),
                    baseline,
                    f"moving the {name!r} sequence must invalidate the documents",
                )

        noisy = dict(sequences, default=sequences["default"] + 1)
        with patch.object(type(self.env.registry), "get_sequences", frozen(noisy)):
            self.assertEqual(
                doc_cache_generation(self.env),
                baseline,
                "the 'default' sequence must not rebuild the index",
            )

    def test_parse_signature(self):
        def clean_doc(d):
            return dict(
                d, doc=inspect.cleandoc(d.get("doc", "")).replace("\n", "").strip()
            )

        methods = inspect.getmembers(DummyMethods, predicate=inspect.isroutine)
        for name, method in methods:
            if name.startswith("__") or not hasattr(method, "expected"):
                continue
            with self.subTest(method=name):
                self.assertEqual(
                    clean_doc(reflect_callable(method).as_dict()),
                    clean_doc(method.expected),
                )

    def test_ghost_model_robustness(self):
        """/doc/index.json skips ir.model rows that are absent from the registry."""

        ghost_model_name = "ir.min.cron.mixin.test.ghost"
        self.env["ir.model"].create(
            {
                "model": ghost_model_name,
                "name": "Ghost Model",
                "state": "base",
            }
        )

        self.authenticate("demo", "demo")
        res = self.url_open("/doc/index.json")
        res.raise_for_status()

    def test_private_methods(self):
        FakeCls = type(
            "ModelDummyMethods",
            (DummyMethods, Model),
            {
                "_name": "model.dummy.methods",
                "_register": False,
                "__module__": "odoo.addons.rpc",
            },
        )
        FakeModel = FakeCls(self.env, (), ())
        assert is_public_method(FakeModel, "one_arg")
        self.assertIn("one_arg", public_method_names(FakeModel))

        for method_name in (
            "class_method",
            "static_method",
            "private_method",
            "_underscope_method",
        ):
            with self.subTest(method_name=method_name):
                assert hasattr(FakeModel, method_name)
                self.assertFalse(is_public_method(FakeModel, method_name))
                self.assertNotIn(method_name, public_method_names(FakeModel))

    def test_describing_docstring_borrows_the_nearest_one(self):
        class Base:
            def name_search(self):
                """Introduced here, documented here."""

        class Middle(Base):
            def name_search(self):
                """The most derived prose wins."""

        class Leaf(Middle):
            def name_search(self):
                pass

        definers = [Leaf, Middle, Base]
        self.assertEqual(
            _describing_docstring(definers, "name_search"),
            "The most derived prose wins.",
        )
        self.assertEqual(
            _describing_docstring([Leaf, Base], "name_search"),
            "Introduced here, documented here.",
        )
        self.assertIsNone(_describing_docstring([Leaf], "name_search"))

    def test_describe_method_provenance_is_the_introducing_layer(self):
        described = describe_method(self.env["res.users"], "name_search")
        self.assertEqual(described["module"], "core")

    def test_describe_method_keeps_the_introducing_signature(self):
        """The signature comes from the base, which is the complete one.

        An override narrowed to ``(*args, **kwargs)`` documents nothing useful.
        """
        described = describe_method(self.env["res.partner"], "search")
        self.assertEqual(
            described["signature"],
            "(domain, offset=0, limit=None, order=None) -> list[int]",
        )

    def test_model_doc_is_the_model_s_own(self):
        """A mixin's prose is not the model's documentation.

        Every mixin `res.partner` inherits sits in the same MRO with its own
        docstring; walking it blindly documents Contact with `mixin.mail.thread`'s
        "allow sending messages related to the current model".
        """
        from odoo.addons.rpc.tools.registry import describe_model_doc

        Partner = self.env["res.partner"]
        doc = describe_model_doc(Partner)
        if doc is not None:
            for mixin in ("mixin.mail.thread", "mixin.avatar", "mixin.image"):
                if mixin in self.env:
                    mixin_doc = type(self.env[mixin]).__doc__
                    if mixin_doc:
                        self.assertNotIn(mixin_doc.strip()[:40], doc)

    def test_model_doc_of_a_documented_model(self):
        """A class that documents itself has that prose published."""
        from odoo.addons.rpc.tools.registry import describe_model_doc

        # A throwaway model class carrying a docstring: that is the prose the
        # page must publish.
        FakeCls = type(
            "DocumentedDummy",
            (Model,),
            {
                "_name": "documented.dummy",
                "_register": False,
                "__module__": "odoo.addons.rpc",
                "__doc__": "A documented dummy model.",
            },
        )
        self.assertIn(
            "A documented dummy model.",
            describe_model_doc(FakeCls(self.env, (), ())),
        )


@tagged("-at_install", "post_install")
class TestDocIndexGeneration(HttpCaseWithUserDemo):
    def test_stale_domain_matches_other_generations_only(self):
        Attachment = self.env["ir.attachment"].sudo()
        Attachment.search([("name", "like", "odoo-doc-index-%")]).unlink()
        generation = doc_cache_generation(self.env)
        current = Attachment.create(
            {"name": f"odoo-doc-index-{generation}-deadbeef.json", "raw": b"{}"}
        )
        stale = Attachment.create(
            {"name": "odoo-doc-index-0000000000-deadbeef.json", "raw": b"{}"}
        )

        matched = Attachment.search(stale_index_domain(generation))
        self.assertIn(stale, matched)
        self.assertNotIn(current, matched)
