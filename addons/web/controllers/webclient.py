import logging
from typing import Any

import odoo.tools
from odoo import http
from odoo.http import Response, request
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.tools.assets.esm_registry import esm_registry

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)
_http_log = get_asset_logger("http")


class WebClient(http.Controller):
    @http.route(
        "/web/webclient/translations",
        type="http",
        auth="public",
        cors="*",
        readonly=True,
    )
    def translations(
        self,
        hash: str | None = None,
        mods: str | None = None,
        lang: str | None = None,
    ) -> Response:
        dbg.lifecycle.debug(
            "[translations] %s lang=%s client_hash=%s explicit_mods=%s",
            dbg.req(),
            lang,
            (hash or "")[:12] or None,
            bool(mods),
        )
        if mods:
            mods = mods.split(",")
        else:
            mods = request.env.registry.loaded_modules.union(
                odoo.tools.config["server_wide_modules"]
            )

        installed_langs = request.env["res.lang"].sudo().get_installed()
        if lang and lang not in {code for code, _ in installed_langs}:
            dbg.logic.debug("[translations] lang %s not installed, dropped", lang)
            lang = None

        with dbg.timer(request.env, "[translations] hash for %d mods", len(mods)):
            current_hash = (
                request.env["ir.http"]
                .with_context(cache_translation_data=True)
                ._get_web_translations_hash(mods, lang)
            )

        body = {
            "lang": lang,
            "hash": current_hash,
        }
        if current_hash != hash:
            if "translation_data" in request.env.cr.cache:
                dbg.logic.debug(
                    "[translations] hash miss: data cached by the hash pass, reused"
                )
                body.update(request.env.cr.cache.pop("translation_data"))
            else:
                dbg.logic.debug("[translations] hash miss: data not cached, rebuilt")
                with dbg.timer(
                    request.env, "[translations] build for %d mods", len(mods)
                ):
                    translations_per_module, lang_params = request.env[
                        "ir.http"
                    ]._get_translations_for_webclient(mods, lang)
                body.update(
                    {
                        "lang_parameters": lang_params,
                        "modules": translations_per_module,
                        "multi_lang": len(installed_langs) > 1,
                    }
                )
            dbg.pipeline.debug(
                "[translations] hash %s -> %d modules in body",
                current_hash[:12],
                len(body.get("modules") or ()),
            )
        else:
            dbg.logic.debug(
                "[translations] hash match %s -> hash only", current_hash[:12]
            )

        return request.prepare_json_response(
            body,
            [
                ("Cache-Control", f"public, max-age={http.STATIC_CACHE_LONG}"),
            ],
        )

    @http.route("/web/webclient/version_info", type="jsonrpc", auth="none")
    def version_info(self) -> dict[str, Any]:
        dbg.lifecycle.debug("[version_info] %s", dbg.req())
        return odoo.service.common.exp_version()

    @http.route("/web/tests", type="http", auth="user", readonly=False)
    def unit_tests_suite(self, mod: str | None = None, **kwargs: Any) -> Response:
        dbg.lifecycle.debug(
            "[tests] suite page: %s mod=%s kwargs=%s", dbg.req(), mod, dbg.keys(kwargs)
        )
        session_info = {"view_info": request.env["ir.ui.view"].get_view_info()}
        scope = request.env["ir.asset"]._get_unit_test_scope()
        dbg.logic.debug("[tests] suite page: unit test scope=%s", scope or None)
        if scope:
            session_info["bundle_params"] = {"module_scope": scope}
        return request.render("web.unit_tests_suite", {"session_info": session_info})

    @http.route(
        "/web/bundle/<string:bundle_name>",
        auth="public",
        methods=["GET"],
        readonly=False,
    )
    def bundle(self, bundle_name: str, **bundle_params: Any) -> Response:
        """Persist cold-generated assets before returning their descriptor URLs."""
        dbg.lifecycle.debug(
            "[bundle:%s] %s params=%s", bundle_name, dbg.req(), dbg.keys(bundle_params)
        )
        if "lang" in bundle_params:
            request.update_context(
                lang=request.env["res.lang"]._get_code(bundle_params["lang"])
            )

        debug = bundle_params.get("debug", request.session.debug)
        page = bundle_params.pop("page", None) or None

        use_esm = bundle_name in esm_registry().bundles
        dbg.logic.debug(
            "[bundle:%s] esm=%s debug=%r page=%s", bundle_name, use_esm, debug, page
        )
        log_event(
            _http_log,
            logging.DEBUG,
            "bundle_request",
            bundle=bundle_name,
            debug=bool(debug),
            is_esm=use_esm,
            params=sorted(bundle_params),
        )

        IrQweb = request.env["ir.qweb"]
        with dbg.timer(request.env, "[bundle:%s] asset nodes", bundle_name):
            if use_esm:
                nodes = IrQweb._links_to_nodes(
                    IrQweb._get_asset_links(bundle_name, debug=debug, js=True, css=True)
                )
            else:
                nodes = IrQweb._get_asset_nodes(
                    bundle_name, debug=debug, js=True, css=True
                )
        data = [
            {
                "type": tag,
                "src": attrs.get("src") or attrs.get("data-src") or attrs.get("href"),
            }
            for tag, attrs in nodes
            if tag != "link" or attrs.get("rel") == "stylesheet"
        ]

        if use_esm:
            with dbg.timer(request.env, "[bundle:%s] esm payload", bundle_name):
                payload = IrQweb._get_esm_bundle_payload(
                    bundle_name,
                    debug_assets=bool(debug) and "assets" in debug,
                    page=page,
                    with_test_satellites=IrQweb._has_esm_test_satellites(debug),
                )
            specifiers = payload["specifiers"]
            import_map = payload["import_map"]
            tpl_url = payload["template_url"]
            esm_url = payload.get("esm_url")
            if not specifiers and not esm_url and not tpl_url:
                dbg.logic.debug(
                    "[bundle:%s] esm payload empty, falling back to legacy", bundle_name
                )
                use_esm = False

        if use_esm:
            data = {
                "is_esm": True,
                "esm_url": esm_url,
                "specifiers": specifiers,
                "import_map": import_map,
                "files": data,
                "template_url": tpl_url,
                "carried": payload.get("carried", False),
            }
            _n_data_uri = sum(1 for v in import_map.values() if v.startswith("data:"))
            _n_real_url = len(import_map) - _n_data_uri
            log_event(
                _http_log,
                logging.INFO,
                "served_esm",
                bundle=bundle_name,
                compiled=bool(esm_url),
                carried=payload.get("carried", False),
                specs=len(specifiers),
                imports=len(import_map),
                url=_n_real_url,
                data=_n_data_uri,
                files=len(data["files"]),
                tpl=bool(tpl_url),
            )
        else:
            log_event(
                _http_log,
                logging.INFO,
                "served_legacy",
                bundle=bundle_name,
                files=len(data),
            )

        return request.prepare_json_response(data)
