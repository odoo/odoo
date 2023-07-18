# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re

from odoo import api, models
from odoo.tools import misc
from odoo.addons.base.models.assetsbundle import EXTENSIONS

_match_asset_file_url_regex = re.compile(r"^(/_custom/([^/]+))?/(\w+)/([/\w]+\.\w+)$")


class Assets(models.AbstractModel):
    _name = 'web_editor.assets'
    _description = 'Assets Utils'

    @api.model
    def reset_asset(self, url, bundle):
        """
        Delete the potential customizations made to a given (original) asset.

        Params:
            url (str): the URL of the original asset (scss / js) file

            bundle (str):
                the name of the bundle in which the customizations to delete
                were made
        """
        custom_url = self._make_custom_asset_url(url, bundle)

        # Simply delete the attachement which contains the modified scss/js file
        # and the xpath view which links it
        self._get_custom_attachment(custom_url).unlink()
        self._get_custom_asset(custom_url).unlink()

    @api.model
    def save_asset(self, url, bundle, content, file_type):
        """
        Customize the content of a given asset (scss / js).

        Params:
            url (src):
                the URL of the original asset to customize (whether or not the
                asset was already customized)

            bundle (src):
                the name of the bundle in which the customizations will take
                effect

            content (src): the new content of the asset (scss / js)

            file_type (src):
                either 'scss' or 'js' according to the file being customized
        """
        custom_url = self._make_custom_asset_url(url, bundle)
        datas = base64.b64encode((content or "\n").encode("utf-8"))

        # Check if the file to save had already been modified
        custom_attachment = self._get_custom_attachment(custom_url)
        if custom_attachment:
            # If it was already modified, simply override the corresponding
            # attachment content
            custom_attachment.write({"datas": datas})
            self.env.registry.clear_cache('assets')
        else:
            # If not, create a new attachment to copy the original scss/js file
            # content, with its modifications
            new_attach = {
                'name': url.split("/")[-1],
                'type': "binary",
                'mimetype': (file_type == 'js' and 'text/javascript' or 'text/scss'),
                'datas': datas,
                'url': custom_url,
                **self._save_asset_attachment_hook(),
            }
            self.env["ir.attachment"].create(new_attach)

            # Create an asset with the new attachment
            IrAsset = self.env['ir.asset']
            new_asset = {
                'path': custom_url,
                'target': url,
                'directive': 'replace',
                **self._save_asset_hook(),
            }
            target_asset = self._get_custom_asset(url)
            if target_asset:
                new_asset['name'] = target_asset.name + ' override'
                new_asset['bundle'] = target_asset.bundle
                new_asset['sequence'] = target_asset.sequence
            else:
                new_asset['name'] = '%s: replace %s' % (bundle, custom_url.split('/')[-1])
                new_asset['bundle'] = IrAsset._get_related_bundle(url, bundle)
            IrAsset.create(new_asset)


    @api.model
    def _get_content_from_url(self, url, url_info=None, custom_attachments=None):
        """
        Fetch the content of an asset (scss / js) file. That content is either
        the one of the related file on the disk or the one of the corresponding
        custom ir.attachment record.

        Params:
            url (str): the URL of the asset (scss / js) file/ir.attachment

            url_info (dict, optional):
                the related url info (see _get_data_from_url) (allows to optimize
                some code which already have the info and do not want this
                function to re-get it)

            custom_attachments (ir.attachment(), optional):
                the related custom ir.attachment records the function might need
                to search into (allows to optimize some code which already have
                that info and do not want this function to re-get it)

        Returns:
            utf-8 encoded content of the asset (scss / js)
        """
        if url_info is None:
            url_info = self._get_data_from_url(url)

        if url_info["customized"]:
            # If the file is already customized, the content is found in the
            # corresponding attachment
            attachment = None
            if custom_attachments is None:
                attachment = self._get_custom_attachment(url)
            else:
                attachment = custom_attachments.filtered(lambda r: r.url == url)
            return attachment and base64.b64decode(attachment.datas) or False

        # If the file is not yet customized, the content is found by reading
        # the local file
        with misc.file_open(url.strip('/'), 'rb', filter_ext=EXTENSIONS) as f:
            return f.read()

    @api.model
    def _get_data_from_url(self, url):
        """
        Return information about an asset (scss / js) file/ir.attachment just by
        looking at its URL.

        Params:
            url (str): the url of the asset (scss / js) file/ir.attachment

        Returns:
            dict:
                module (str): the original asset's related app

                resource_path (str):
                    the relative path to the original asset from the related app

                customized (bool): whether the asset is a customized one or not

                bundle (str):
                    the name of the bundle the asset customizes (False if this
                    is not a customized asset)
        """
        m = _match_asset_file_url_regex.match(url)
        if not m:
            return False
        return {
            'module': m.group(3),
            'resource_path': m.group(4),
            'customized': bool(m.group(1)),
            'bundle': m.group(2) or False
        }

    @api.model
    def _make_custom_asset_url(self, url, bundle_xmlid):
        """
        Return the customized version of an asset URL, that is the URL the asset
        would have if it was customized.

        Params:
            url (str): the original asset's url
            bundle_xmlid (str): the name of the bundle the asset would customize

        Returns:
            str: the URL the given asset would have if it was customized in the
                 given bundle
        """
        return f"/_custom/{bundle_xmlid}{url}"

    @api.model
    def _get_custom_attachment(self, custom_url, op='='):
        """
        Fetch the ir.attachment record related to the given customized asset.

        Params:
            custom_url (str): the URL of the customized asset
            op (str, default: '='): the operator to use to search the records

        Returns:
            ir.attachment()
        """
        assert op in ('in', '='), 'Invalid operator'
        return self.env["ir.attachment"].search([("url", op, custom_url)])

    @api.model
    def _get_custom_asset(self, custom_url):
        """
        Fetch the ir.asset record related to the given customized asset (the
        inheriting view which replace the original asset by the customized one).

        Params:
            custom_url (str): the URL of the customized asset

        Returns:
            ir.asset()
        """
        url = custom_url[1:] if custom_url.startswith(('/', '\\')) else custom_url
        return self.env['ir.asset'].search([('path', 'like', url)])

    @api.model
    def _save_asset_attachment_hook(self):
        """
        Returns the additional values to use to write the DB on customized
        ir.attachment creation.

        Returns:
            dict
        """
        return {}

    @api.model
    def _save_asset_hook(self):
        """
        Returns the additional values to use to write the DB on customized
        ir.asset creation.

        Returns:
            dict
        """
        return {}
