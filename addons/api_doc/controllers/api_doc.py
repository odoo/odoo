import hashlib
import json
import logging
from http import HTTPStatus

from werkzeug.exceptions import NotFound
from werkzeug.http import is_resource_modified, parse_cache_control_header

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import SQL, hmac, json_default, py_to_js_locale

from ..tools.cache import (
    doc_cache_generation,
    index_attachment_name,
    stale_index_domain,
)
from ..tools.registry import describe_method, describe_model_doc, public_method_names

logger = logging.getLogger(__name__)


class DocController(http.Controller):
    """Single page application exposing an OpenAPI-like reflection of the
    registry (fields and methods) as JSON documents.
    """

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @http.route(
        ["/doc", "/doc/<model_name>", "/doc/index.html"], type="http", auth="user"
    )
    def doc_client(self, **kwargs):
        self._check_doc_access()
        res = request.render("api_doc.docclient")
        res.headers["X-Frame-Options"] = "deny"
        return res

    @http.route("/doc-bearer/index.json", type="json2", auth="bearer", typed=True)
    def doc_bearer_index(self):
        return self.doc_index()

    @http.route("/doc/index.json", type="json2", auth="user", typed=True)
    def doc_index(self):
        """Get a listing of all models, methods and fields, limited to their
        technical name and translated "human" name.

        :return: an HTTP response whose body is a JSON document with the
            following structure:

            .. code-block:: python

                {
                    'models': [
                        {
                            'model': str,
                            'name': str,
                            'fields': {field_name: {'string': str}},
                            'methods': list[str],
                        }
                        for model in ...
                    ]
                }
        :rtype: werkzeug.wrappers.Response
        :raises AccessError: the user is not in ``api_doc.group_allow_doc``
        """
        self._check_doc_access()

        generation = doc_cache_generation(self.env)
        unique = self._doc_cache_key("/doc/index.json", generation)
        use_cache = self._client_accepts_cache()
        if use_cache and not is_resource_modified(
            request.httprequest.environ, etag=unique
        ):
            return request.prepare_response("", status=HTTPStatus.NOT_MODIFIED)

        # Server cache: an attachment rather than an ormcache entry, because
        # the index runs to megabytes once many modules are installed.
        # TODO: gzip
        filename = index_attachment_name(generation, unique)
        index_attach = (
            self.env["ir.attachment"].sudo().search([("name", "=", filename)], limit=1)
        )
        if not index_attach or not use_cache:
            index_attach = self._doc_index_cache(
                filename, generation, refresh=not use_cache
            )

        response = index_attach._to_http_stream().prepare_response(etag=unique)
        response.headers["Content-Language"] = py_to_js_locale(self.env.lang)
        return response

    @http.route(
        "/doc-bearer/<model_name>.json",
        type="json2",
        auth="bearer",
        readonly=True,
        typed=True,
    )
    def doc_bearer_model(self, model_name: str):
        return self.doc_model(model_name)

    @http.route(
        "/doc/<model_name>.json", type="json2", auth="user", readonly=True, typed=True
    )
    def doc_model(self, model_name: str):
        """Get a complete listing of the fields and methods of one model: an
        enriched ``fields_get()`` plus, for each method, its signature,
        parameters and htmlified docstring.

        :param str model_name: technical name of the model to reflect
        :return: an HTTP response whose body is a JSON document with the
            following structure:

            .. code-block:: python

                {
                    'model': str,
                    'name': str,
                    'doc': str | None,  # htmlified model docstring
                    'fields': dict[str, dict],  # fields_get indexed by field name
                    'methods': dict[str, dict],  # describe_method indexed by name
                }
        :rtype: werkzeug.wrappers.Response
        :raises AccessError: the user is not in ``api_doc.group_allow_doc``
        :raises NotFound: ``model_name`` is not in the registry
        """
        self._check_doc_access()
        if model_name not in self.env:
            raise NotFound

        Model = self.env[model_name]
        Model.check_access("read")
        ir_model = self.env["ir.model"]._get(model_name)

        unique = self._doc_cache_key(
            "/doc/<model_name>.json", doc_cache_generation(self.env)
        )
        use_cache = self._client_accepts_cache()
        if use_cache and not is_resource_modified(
            request.httprequest.environ, etag=unique
        ):
            return request.prepare_response("", status=HTTPStatus.NOT_MODIFIED)

        result = {
            "model": model_name,
            "name": ir_model.name,
            "doc": describe_model_doc(Model),
            "fields": {
                field["name"]: dict(
                    field,
                    module=next(iter(Model._fields[field["name"]]._modules), None),
                )
                for field in Model.fields_get().values()
            },
            "methods": {
                method_name: describe_method(Model, method_name)
                for method_name in public_method_names(Model)
            },
        }

        response = request.prepare_json_response(result)
        response.set_etag(unique)
        response.headers["Cache-Control"] = "no-cache, private"  # no-cache != no-store
        response.headers["Content-Language"] = py_to_js_locale(self.env.lang)
        return response

    # ------------------------------------------------------------------
    # Access, caching
    # ------------------------------------------------------------------

    def _check_doc_access(self):
        """Every ``/doc`` route is gated on the same group.

        :raises AccessError: the user is not in ``api_doc.group_allow_doc``
        """
        if not self.env.user.has_group("api_doc.group_allow_doc"):
            raise AccessError(
                self.env._(
                    "This page is only accessible to %s users.",
                    self.env.ref("api_doc.group_allow_doc").sudo().name,
                )
            )

    def _doc_cache_key(self, scope, generation):
        """The ETag for a ``/doc`` document.

        Everything the document's *content* depends on has to be in here: the
        database state (``generation``, which covers module installs and access
        changes alike), the language the labels are translated into, and the
        groups that decide which models and fields the reader may see.

        :param str scope: the route this key is for, so two routes cannot
            collide on one ETag
        :param str generation: from
            :func:`~odoo.addons.api_doc.tools.cache.doc_cache_generation`
        :return: an hmac over the cache inputs
        :rtype: str
        """
        return hmac(
            self.env(su=True),
            scope=scope,
            message=(
                generation,
                self.env.lang,
                sorted(self.env.user.all_group_ids.ids),
            ),
        )

    def _client_accepts_cache(self):
        """Whether the client is willing to be served a cached document."""
        cache_control = parse_cache_control_header(
            request.httprequest.headers.get("Cache-Control")
        )
        return not cache_control.no_cache

    def _doc_index_cache(self, filename, generation, refresh):
        """Return the cached index attachment, generating it if needed.

        Serialised with an advisory lock: the index costs seconds to build on a
        large registry, and without the lock every concurrent first request
        builds its own copy and stores a duplicate row that nothing collects.

        :param str filename: the cache key, as an attachment name
        :param str generation: the current cache generation
        :param bool refresh: regenerate even when the attachment already exists
        :return: the attachment holding the index
        :rtype: odoo.model.ir_attachment
        """
        # blake2b rather than hash(): the lock key must be stable across
        # processes, which PYTHONHASHSEED makes str.__hash__ not.
        digest = hashlib.blake2b(filename.encode(), digest_size=8).digest()
        self.env.cr.execute(
            SQL(
                "SELECT pg_advisory_xact_lock(%s)",
                int.from_bytes(digest, "big", signed=True),
            )
        )

        Attachment = self.env["ir.attachment"].sudo()
        # Re-read under the lock: whoever held it before us may have been here
        # for exactly this reason.
        index_attach = Attachment.search([("name", "=", filename)], limit=1)
        if index_attach and not refresh:
            return index_attach

        payload = json.dumps(
            {"models": self._doc_index()},
            ensure_ascii=False,
            default=json_default,
        )
        if index_attach:
            # The client asked for a fresh document: keep the server-side cache
            # in sync instead of discarding what we just computed.
            index_attach.raw = payload
            logger.info("refreshed index attachment: %s", filename)
        else:
            index_attach = Attachment.create(
                {
                    "name": filename,
                    "description": (
                        "Generated /doc/index.json document.\n\n"
                        f"Lang: {self.env.lang}\n"
                        f"Groups: {sorted(self.env.user.all_group_ids.ids)}"
                    ),
                    "mimetype": "application/json; charset=utf-8",
                    "raw": payload,
                    "public": False,
                }
            )
            logger.info("new index attachment: %s", filename)

        # Building a new generation makes every older one unservable. The
        # autovacuum would collect them eventually; doing it here keeps the
        # table from carrying a day of them, and costs one query.
        superseded = Attachment.search(stale_index_domain(generation))
        if superseded:
            superseded.unlink()
            logger.info(
                "dropped %s superseded /doc index attachment(s)", len(superseded)
            )
        return index_attach

    def _doc_index(self):
        """The index document's ``models`` entry.

        :return: one dict per readable model, holding names only
        :rtype: list[dict]
        """
        return [
            {
                "model": ir_model.model,
                "name": ir_model.name,
                "fields": {
                    field.name: {"string": field.field_description}
                    for field in ir_model.field_id
                    # Skip stale ir.model.fields rows whose Python field was
                    # removed without cleaning up the metadata (e.g. a refactor
                    # without a migration script). Crashing /doc on the first
                    # orphan would hide the rest of the registry.
                    if (python_field := Model._fields.get(field.name)) is not None
                    and Model._has_field_access(python_field, "read")
                },
                "methods": public_method_names(Model),
            }
            for ir_model in self.env["ir.model"].sudo().search([])
            if ir_model.model in self.env
            if (Model := self.env[ir_model.model]).has_access("read")
        ]
