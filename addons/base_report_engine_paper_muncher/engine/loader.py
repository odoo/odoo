# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from contextlib import nullcontext

from odoo import SUPERUSER_ID, api, _
from odoo.exceptions import UserError
from odoo.addons.base.models.assetsbundle import ANY_UNIQUE


_logger = logging.getLogger(__name__)


class OdooLoader:

    def __init__(self, env, document, doc_name):
        self.env = env
        self.document = document
        self.doc_name = doc_name

    # COPIED FROM CONTROLLER, TODO
    def _get_assets(self, filename=None, unique=ANY_UNIQUE, assets_params=None):
        assets_params = assets_params or {}
        assert isinstance(assets_params, dict)
        debug_assets = unique == 'debug'
        if unique in ('any', '%'):
            unique = ANY_UNIQUE
        attachment = None
        if unique != 'debug':
            url = self.env['ir.asset']._get_asset_bundle_url(filename, unique, assets_params)
            assert not '%' in url
            domain = [
                ('public', '=', True),
                ('url', '!=', False),
                ('url', '=like', url),
                ('res_model', '=', 'ir.ui.view'),
                ('res_id', '=', 0),
                ('create_uid', '=', SUPERUSER_ID),
            ]
            attachment = self.env['ir.attachment'].sudo().search(domain, limit=1)
        if not attachment:
            # try to generate one
            if self.env.cr.readonly:
                self.env.cr.rollback()  # reset state to detect newly generated assets
                cursor_manager = self.env.registry.cursor(readonly=False)
            else:
                # if we don't have a replica, the cursor is not readonly, use the same one to avoid a rollback
                cursor_manager = nullcontext(self.env.cr)
            with cursor_manager as rw_cr:
                rw_env = api.Environment(rw_cr, self.env.user.id, {})
                try:
                    if filename.endswith('.map'):
                        _logger.error(".map should have been generated through debug assets, (version %s most likely outdated)", unique)
                        raise UserError(_("The requested asset %s is not available. Please reload the page to get the latest version."), filename)
                    bundle_name, rtl, asset_type, autoprefix = rw_env['ir.asset']._parse_bundle_name(filename, debug_assets)
                    css = asset_type == 'css'
                    js = asset_type == 'js'
                    bundle = rw_env['ir.qweb']._get_asset_bundle(
                        bundle_name,
                        css=css,
                        js=js,
                        debug_assets=debug_assets,
                        rtl=rtl,
                        autoprefix=autoprefix,
                        assets_params=assets_params,
                    )
                    # check if the version matches. If not, redirect to the last version
                    if not debug_assets and unique != ANY_UNIQUE and unique != bundle.get_version(asset_type):
                        return UserError(_("The requested asset %s is not available. Please reload the page to get the latest version."), filename)
                    if css and bundle.stylesheets:
                        attachment = self.env['ir.attachment'].sudo().browse(bundle.css().id)
                    elif js and bundle.javascripts:
                        attachment = self.env['ir.attachment'].sudo().browse(bundle.js().id)
                except ValueError as e:
                    _logger.warning("Parsing asset bundle %s has failed: %s", filename, e)
                    raise FileNotFoundError()
        if not attachment:
            raise FileNotFoundError()

        return self.env['ir.binary']._get_stream_from(attachment, 'raw', filename)

    def handleRequest(self, url: str):
        # FIXME: we dont need to reload the document which is already in `body`, but this check should be more elegant
        url_nodes = url.split("/")

        if url_nodes[-1].replace('.html', '') == self.doc_name or url == self.doc_name:
            return self.document

        # Assets path: /web/assets/<string:unique>/<string:filename>'
        if len(url_nodes) == 5 and url.startswith("/web/assets/"):
            assetBinary = self._get_assets(url_nodes[-1], url_nodes[-2])
            return assetBinary.read()

        raise FileNotFoundError()
