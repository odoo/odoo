# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Assets(models.AbstractModel):
    _inherit = 'web_editor.assets'

    def get_view_fields_to_read(self):
        res = super(Assets, self).get_view_fields_to_read()
        res.append('website_id')
        return res

    def _get_custom_attachment(self, custom_url, op='='):
        """
        See web_editor.Assets._get_custom_attachment
        Extend to only return the attachments related to the current website.
        """
        website = self.env['website'].get_current_website()
        res = super(Assets, self)._get_custom_attachment(custom_url, op=op)
        return res.with_context(website_id=website.id).filtered(lambda x: not x.website_id or x.website_id == website)

    def _get_custom_view(self, custom_url, op='='):
        """
        See web_editor.Assets._get_custom_view
        Extend to only return the views related to the current website.
        """
        website = self.env['website'].get_current_website()
        res = super(Assets, self)._get_custom_view(custom_url, op=op)
        return res.with_context(website_id=website.id).filter_duplicate()

    def _save_asset_attachment_hook(self):
        """
        See web_editor.Assets._save_asset_attachment_hook
        Extend to add website ID at attachment creation.
        """
        res = super(Assets, self)._save_asset_attachment_hook()

        website = self.env['website'].get_current_website()
        if website:
            res['website_id'] = website.id
        return res

    def _save_asset_view_hook(self):
        """
        See web_editor.Assets._save_asset_view_hook
        Extend to add website ID at view creation.
        """
        res = super(Assets, self)._save_asset_view_hook()

        website = self.env['website'].get_current_website()
        if website:
            res['website_id'] = website.id
        return res
