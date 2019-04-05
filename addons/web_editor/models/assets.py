# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import os
import re
import uuid

from lxml import etree

from odoo import models
from odoo.modules.module import get_resource_path, get_module_path

_match_asset_file_url_regex = re.compile("^/(\w+)/(.+?)(\.custom\.(.+))?\.(\w+)$")


class Assets(models.AbstractModel):
    _name = 'web_editor.assets'
    _description = 'Assets Utils'

    def get_all_custom_attachments(self, urls):
        """
        Fetch all the ir.attachment records related to given URLs.

        Params:
            urls (str[]): list of urls

        Returns:
            ir.attachment(): attachment records related to the given URLs.
        """
        return self._get_custom_attachment(urls, op='in')

    def get_asset_content(self, url, url_info=None, custom_attachments=None):
        """
        Fetch the content of an asset (scss / js) file. That content is either
        the one of the related file on the disk or the one of the corresponding
        custom ir.attachment record.

        Params:
            url (str): the URL of the asset (scss / js) file/ir.attachment

            url_info (dict, optional):
                the related url info (see get_asset_info) (allows to optimize
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
            url_info = self.get_asset_info(url)

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
        # the local scss file
        module = url_info["module"]
        module_path = get_module_path(module)
        module_resource_path = get_resource_path(module, url_info["resource_path"])
        if module_path and module_resource_path:
            module_path = os.path.join(os.path.normpath(module_path), '')  # join ensures the path ends with '/'
            module_resource_path = os.path.normpath(module_resource_path)
            if module_resource_path.startswith(module_path):
                with open(module_resource_path, "rb") as f:
                    return f.read()

    def get_asset_info(self, url):
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
            'module': m.group(1),
            'resource_path': "%s.%s" % (m.group(2), m.group(5)),
            'customized': bool(m.group(3)),
            'bundle': m.group(4) or False
        }

    def make_custom_asset_file_url(self, url, bundle_xmlid):
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
        parts = url.rsplit(".", 1)
        return "%s.custom.%s.%s" % (parts[0], bundle_xmlid, parts[1])

    def reset_asset(self, url, bundle_xmlid):
        """
        Delete the potential customizations made to a given (original) asset.

        Params:
            url (str): the URL of the original asset (scss / js) file

            bundle_xmlid (str):
                the name of the bundle in which the customizations to delete
                were made
        """
        custom_url = self.make_custom_asset_file_url(url, bundle_xmlid)

        # Simply delete the attachement which contains the modified scss/js file
        # and the xpath view which links it
        self._get_custom_attachment(custom_url).unlink()
        self._get_custom_view(custom_url).unlink()

    def save_asset(self, url, bundle_xmlid, content, file_type):
        """
        Customize the content of a given asset (scss / js).

        Params:
            url (src):
                the URL of the original asset to customize (whether or not the
                asset was already customized)

            bundle_xmlid (src):
                the name of the bundle in which the customizations will take
                effect

            content (src): the new content of the asset (scss / js)

            file_type (src):
                either 'scss' or 'js' according to the file being customized
        """
        custom_url = self.make_custom_asset_file_url(url, bundle_xmlid)
        datas = base64.b64encode((content or "\n").encode("utf-8"))

        # Check if the file to save had already been modified
        custom_attachment = self._get_custom_attachment(custom_url)
        if custom_attachment:
            # If it was already modified, simply override the corresponding
            # attachment content
            custom_attachment.write({"datas": datas})
        else:
            # If not, create a new attachment to copy the original scss/js file
            # content, with its modifications
            new_attach = {
                'name': url.split("/")[-1],
                'type': "binary",
                'mimetype': (file_type == 'js' and 'text/javascript' or 'text/scss'),
                'datas': datas,
                'url': custom_url,
            }
            new_attach.update(self._save_asset_attachment_hook())
            self.env["ir.attachment"].create(new_attach)

            # Create a view to extend the template which adds the original file
            # to link the new modified version instead
            file_type_info = {
                'tag': 'link' if file_type == 'scss' else 'script',
                'attribute': 'href' if file_type == 'scss' else 'src',
            }

            def views_linking_url(view):
                """
                Returns whether the view arch has some html tag linked to
                the url. (note: searching for the URL string is not enough as it
                could appear in a comment or an xpath expression.)
                """
                tree = etree.XML(view.arch)
                return bool(tree.xpath("//%%(tag)s[@%%(attribute)s='%(url)s']" % {
                    'url': url,
                } % file_type_info))

            IrUiView = self.env["ir.ui.view"]
            view_to_xpath = IrUiView.get_related_views(bundle_xmlid, bundles=True).filtered(views_linking_url)
            new_view = {
                'name': custom_url,
                'key': 'web_editor.%s_%s' % (file_type, str(uuid.uuid4())[:6]),
                'mode': "extension",
                'inherit_id': view_to_xpath.id,
                'arch': """
                    <data inherit_id="%(inherit_xml_id)s" name="%(name)s">
                        <xpath expr="//%%(tag)s[@%%(attribute)s='%(url_to_replace)s']" position="attributes">
                            <attribute name="%%(attribute)s">%(new_url)s</attribute>
                        </xpath>
                    </data>
                """ % {
                    'inherit_xml_id': view_to_xpath.xml_id,
                    'name': custom_url,
                    'url_to_replace': url,
                    'new_url': custom_url,
                } % file_type_info
            }
            new_view.update(self._save_asset_view_hook())
            IrUiView.create(new_view)

        self.env["ir.qweb"].clear_caches()

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

    def _get_custom_view(self, custom_url, op='='):
        """
        Fetch the ir.ui.view record related to the given customized asset (the
        inheriting view which replace the original asset by the customized one).

        Params:
            custom_url (str): the URL of the customized asset
            op (str, default: '='): the operator to use to search the records

        Returns:
            ir.ui.view()
        """
        assert op in ('='), 'Invalid operator'
        return self.env["ir.ui.view"].search([("name", op, custom_url)])

    def _save_asset_attachment_hook(self):
        """
        Returns the additional values to use to write the DB on customized
        attachment creation.

        Returns:
            dict
        """
        return {}

    def _save_asset_view_hook(self):
        """
        Returns the additional values to use to write the DB on customized
        asset's related view creation.

        Returns:
            dict
        """
        return {}
