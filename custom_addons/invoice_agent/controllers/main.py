"""HTTP + JSON-RPC endpoints for the invoice_agent module.

This file is the *teaching core* of the module: it exercises every piece of
the Odoo 19 HTTP stack documented in ``docs/tutorial_http_controllers.md``:

* ``@http.route(type='http', auth='none', methods=['POST'], csrf=False)``
* ``@http.route(type='jsonrpc', auth='bearer')`` -- Odoo 19: ``type='json'``
  is a deprecated alias, see the ``route()`` decorator in ``odoo/http.py``.
  ``auth='bearer'`` accepts a session (interactive browser, which sends the
  Sec-Fetch headers) or, for machine clients, an ``Authorization: Bearer``
  API key — the status poll route is a machine endpoint, same as upload.
* Reading ``request.httprequest.files`` from a ``multipart/form-data`` POST
* Storing an ``ir.attachment`` with the ``raw`` field (binary, not ``datas``)
* Auth via ``Authorization: Bearer <key>`` resolved against
  ``res.users.apikeys._check_credentials(scope='rpc', key=key)``
* ``request.update_env(user=uid)`` to rebind the ORM environment
* Clean ``werkzeug.exceptions.BadRequest`` / JSON ``Unauthorized`` responses
  instead of leaked tracebacks

Why ``auth='none'`` on the upload route:

  Odoo's ``auth='user'`` pre-filter runs *before* the endpoint and raises
  ``SessionExpiredException`` for anonymous sessions, which the
  ``HttpDispatcher`` turns into a redirect to ``/web/login`` (HTML). This
  endpoint is a machine route: we want the bearer decorator to be the *only*
  authentication layer so that every unauthenticated attempt (missing key,
  revoked key, wrong scope) gets a JSON 401, never an HTML login page.
  ``auth='none'`` deactivates the session pre-filter (``ir.http._auth_method_none``
  sets ``request.env`` uid to ``None``) and lets the decorator decide. We also
  pass ``save_session=False`` so no session cookie is ever written -- the same
  behaviour Odoo applies automatically to ``auth='bearer'`` routes.

  If you switch this route to ``auth='user'`` or ``auth='public'`` you can
  observe the deliberate auth-mode failures described in the tutorial.
"""

import functools
import logging
import time

from werkzeug.exceptions import BadRequest, NotFound, Unauthorized

from odoo import http
from odoo.http import request
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

# Upload guards: 10 MiB limit and PDF-only mimetypes.
# Kept as module constants so tests can reach them and so the policy is
# decided in exactly one place.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIMETYPES = ("application/pdf",)


def _unauthorized_json(message):
    """Build a werkzeug 401 exception whose body is JSON, not an HTML page."""
    body = request.make_json_response(
        {"error": {"message": message}},
        status=401,
    )
    return Unauthorized(response=body)


def _require_bearer_auth(endpoint):
    """Decorator: authenticate a machine-to-machine HTTP call with an API key.

    The route uses ``auth='none'`` so the session layer never intercepts the
    request. This decorator is the single authentication gate:

    * missing key        -> JSON 401
    * unknown / revoked /
      wrong-scope key    -> JSON 401
    * valid key          -> ``request.update_env(user=uid)`` rebinds the ORM
      environment, so every ``request.env`` call in the endpoint runs as that
      user, then calls the real endpoint.

    ``_check_credentials(scope='rpc', key=...)`` is the same call used by the
    XML-RPC layer and by ``ir.http._auth_method_bearer`` in Odoo 19. Scope
    ``'rpc'`` matches keys whose ``scope`` column is NULL (global keys) or
    exactly ``'rpc'`` -- see ``res_users._check_apikey_credentials``.
    """

    @functools.wraps(endpoint)
    def wrapper(self, *args, **kwargs):
        httprequest = request.httprequest
        authorization = httprequest.headers.get("Authorization", "")
        scheme, _separator, token = authorization.partition(" ")

        if scheme.lower() != "bearer" or not token.strip():
            _logger.warning(
                "Unauthorized upload attempt (missing bearer token) from %s",
                httprequest.remote_addr,
            )
            msg = "Missing Bearer API key in Authorization header"
            raise _unauthorized_json(
                msg,
            )

        apikeys = request.env["res.users.apikeys"]
        uid = apikeys._check_credentials(scope="rpc", key=token.strip())
        if not uid:
            _logger.warning(
                "Unauthorized upload attempt (invalid API key) from %s",
                httprequest.remote_addr,
            )
            msg = "Invalid, revoked or wrong-scope API key"
            raise _unauthorized_json(
                msg,
            )

        # Rebind the ORM environment to the API-key user. This is exactly what
        # ir.http._auth_method_bearer does after a successful key check.
        request.update_env(user=uid)
        return endpoint(self, *args, **kwargs)

    return wrapper


class InvoiceAgentController(http.Controller):
    # ------------------------------------------------------------------
    # POST /invoice_agent/upload  (multipart/form-data, machine route)
    # ------------------------------------------------------------------
    @http.route(
        "/invoice_agent/upload",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        save_session=False,
        readonly=False,
    )
    @_require_bearer_auth
    def invoice_agent_upload(self, **kwargs):
        """Accept a PDF, store it as an ir.attachment, create a draft
        account.move (bill) with ``ai_extraction_status='pending'`` and return
        the new move's id as JSON.

        Note on ``csrf=False`` (justification, mirror of the ``/web/database/*``
        family in ``addons/web/controllers/database.py``): this is a machine
        route authenticated by a bearer API key, not a browser form. CSRF
        protects browser sessions from cross-site form posts; a bearer token in
        the Authorization header is *not* automatically attached by browsers,
        so the classic CSRF attack vector does not apply. Browser form posts
        should stay ``csrf=True`` (the default).
        """
        httprequest = request.httprequest
        remote_addr = httprequest.remote_addr

        upload = httprequest.files.get("file")
        if upload is None:
            _logger.warning("Upload without 'file' part from %s", remote_addr)
            raise BadRequest(
                _("Missing 'file' part in multipart/form-data upload."),
            )

        raw = upload.read() if hasattr(upload, "read") else upload
        filename = upload.filename or "invoice.pdf"
        content_type = (upload.content_type or "").lower()

        if len(raw) > MAX_UPLOAD_BYTES:
            _logger.warning(
                "Rejected oversized upload (%d bytes > %d) from %s",
                len(raw),
                MAX_UPLOAD_BYTES,
                remote_addr,
            )
            raise BadRequest(
                _(
                    "File too large: %(size)d MiB exceeds the %(max)d MiB limit.",
                )
                % {
                    "size": len(raw) // (1024 * 1024),
                    "max": MAX_UPLOAD_BYTES // (1024 * 1024),
                },
            )

        if content_type not in ALLOWED_MIMETYPES:
            _logger.warning(
                "Rejected non-PDF upload (mimetype=%r) from %s",
                content_type,
                remote_addr,
            )
            raise BadRequest(
                _(
                    "Unsupported file type %(mime)s: only %(allowed)s are accepted.",
                )
                % {
                    "mime": content_type or "unknown",
                    "allowed": ", ".join(ALLOWED_MIMETYPES),
                },
            )

        # ---- Manual bearer-token authentication (from _require_bearer_auth) ----
        authorization = httprequest.headers.get("Authorization", "")
        scheme, _separator, token = authorization.partition(" ")

        if scheme.lower() != "bearer" or not token.strip():
            _logger.warning(
                "Unauthorized upload attempt (missing bearer token) from %s",
                httprequest.remote_addr,
            )
            msg = "Missing Bearer API key in Authorization header"
            raise _unauthorized_json(
                msg,
            )

        apikeys = request.env["res.users.apikeys"]
        uid = apikeys._check_credentials(scope="rpc", key=token.strip())
        if not uid:
            _logger.warning(
                "Unauthorized upload attempt (invalid API key) from %s",
                httprequest.remote_addr,
            )
            msg = "Invalid, revoked or wrong-scope API key"
            raise _unauthorized_json(
                msg,
            )
        request.update_env(user=uid)

        # ---- Store the source document ----
        attachment = request.env["ir.attachment"].create(
            {
                "name": filename,
                "raw": raw,  # Binary field: raw bytes, no base64 dance
                "mimetype": content_type,
                "res_model": "account.move",
                "res_id": 0,  # Unbound until the move exists; linked below
            },
        )

        # ---- Create the draft bill in the extraction state machine ----
        # ``ocr_state`` defaults to 'pending' but is written explicitly so
        # the OCR cron (data/cron.xml) claims the record on its next tick —
        # the contract with the queue is visible in the create call itself.
        move = request.env["account.move"].create(
            {
                "move_type": "in_invoice",  # vendor bill
                "ai_source_attachment_id": attachment.id,
                "ai_extraction_status": "pending",
                "ocr_state": "pending",
                "ai_confidence": 0.0,
            },
        )
        if move:
            attachment.write({"res_id": move.id})

        # ---- Enqueue the extraction hook (placeholder; the real OCR/Claude
        # work runs on the queue worker). The move is 'pending', which is what
        # the status endpoint reports to polling clients. ----
        try:
            move._invoice_agent_schedule_extraction()
        except Exception:
            # Never turn a queueing error into a client-visible traceback.
            _logger.exception(
                "Failed to enqueue extraction for move %d",
                move.id,
            )

        # ---- Audit trail ----
        _logger.info(
            "invoice_agent upload: move_id=%d attachment_id=%d user=%s uid=%d from %s",
            move.id,
            attachment.id,
            request.env.user.login,
            request.env.uid,
            remote_addr,
        )

        return request.make_json_response(
            {
                "jsonrpc": "2.0",
                "id": None,
                "result": {
                    "move_id": move.id,
                    "name": move.name or "DRAFT",
                    "state": "draft",
                    "ai_extraction_status": move.ai_extraction_status,
                },
            },
            status=201,
        )

    # ------------------------------------------------------------------
    # POST /invoice_agent/measure/trigger  (dev-only measurement route)
    # ------------------------------------------------------------------
    # Dev-only endpoint that exercises the *exact* worker hold of a real
    # Claude call without credentials or API spend: it runs
    # ``invoice.llm.service.extract_invoice`` synchronously inside a regular
    # HTTP worker. When the ``invoice_agent.measure_delay`` config parameter
    # is set (seconds), ``_client()`` sleeps inside the worker for that
    # duration before failing on the missing API key — the elapsed time
    # returned is the proof that one extraction holds one HTTP worker for
    # the full Claude round-trip.
    #
    # Used by scripts/measure_blocking.py (ADR-003 evidence). Not for
    # production use: no authentication, no rate limiting, deliberately
    # minimal.
    # ------------------------------------------------------------------
    @http.route(
        "/invoice_agent/measure/trigger",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def invoice_agent_measure_trigger(self, **kwargs):
        """Run one synchronous Claude client-construction inside this worker.

        Returns the wall-clock time the worker spent inside the Claude call
        path (the ``measure_delay`` sleep in ``invoice.llm.service._client``).
        A 200 response with ``elapsed_seconds`` near the configured delay is
        the measured proof that the request occupied a whole worker process
        for the duration — exactly where a real Claude round-trip holds it.

        """
        started = time.monotonic()
        try:
            self.env["invoice.llm.service"].extract_invoice(
                "MEASURE-PLACEHOLDER TEXT",
            )
        except Exception as exc:
            _logger.info(
                "invoice_agent measure trigger: extraction raised %s after %.2fs",
                type(exc).__name__,
                time.monotonic() - started,
            )
        return request.make_json_response(
            {
                "jsonrpc": "2.0",
                "id": None,
                "result": {
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "endpoint": "/invoice_agent/measure/trigger",
                },
            },
            status=200,
        )

    # ------------------------------------------------------------------
    # POST /invoice_agent/status/<int:move_id>  (JSON-RPC, poll endpoint)
    # ------------------------------------------------------------------
    @http.route(
        "/invoice_agent/status/<int:move_id>",
        type="jsonrpc",
        auth="bearer",
        methods=["POST"],
        csrf=False,
        readonly=False,
    )
    def invoice_agent_status(self, move_id, **kwargs):
        """Return the extraction state and confidence for a bill, so clients
        can poll while OCR + Claude run in the background.

        Odoo 19 detail: ``type='jsonrpc'`` is the current spelling;
        ``type='json'`` is a deprecated alias that emits a DeprecationWarning
        (see the ``route()`` decorator in ``odoo/http.py``).

        Auth mode: ``auth='bearer'`` accepts a session (interactive browser,
        which sends the Sec-Fetch browser headers) or — for machine clients —
        an ``Authorization: Bearer <api-key>`` header. A poller with no
        session and no key gets a JSON-RPC error envelope instead of an HTML
        redirect, like the upload route's JSON 401.

        The JSON-RPC 2.0 envelope is produced by ``JsonRPCDispatcher``: the
        route returns a plain dict and the dispatcher wraps it into
        ``{"jsonrpc": "2.0", "id": ..., "result": {...}}``.
        """
        move = request.env["account.move"].browse(move_id)
        if not move.exists():
            raise NotFound(f"account.move {move_id} does not exist")

        return {
            "move_id": move.id,
            "ai_extraction_status": move.ai_extraction_status,
            "ai_confidence": move.ai_confidence,
            "ai_review_required": move.ai_review_required,
            "ocr_state": move.ocr_state,
            "ocr_confidence": move.ocr_confidence,
            "ocr_error_message": move.ocr_error_message,
        }
