# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrAsset(models.Model):
    _inherit = 'ir.asset'

    key = fields.Char(copy=False) # used to resolve multiple assets in a multi-website environment
    website_id = fields.Many2one('website', ondelete='cascade')

    def _get_related_assets(self, domain):
        website = self.env['website'].get_current_website(fallback=False)
        if website:
            domain += website.website_domain()
        assets = super()._get_related_assets(domain)
        return assets.filter_duplicate()

    def _get_active_addons_list(self):
        """Overridden to discard inactive themes."""
        addons_list = super()._get_active_addons_list()
        website = self.env['website'].get_current_website(fallback=False)

        if not website:
            return addons_list

        IrModule = self.env['ir.module.module'].sudo()
        # discard all theme modules except website.theme_id
        themes = IrModule.search(IrModule.get_themes_domain()) - website.theme_id
        to_remove = set(themes.mapped('name'))

        return [name for name in addons_list if name not in to_remove]

    def filter_duplicate(self):
        """ Filter current recordset only keeping the most suitable asset per distinct name.
            Every non-accessible asset will be removed from the set:
              * In non website context, every asset with a website will be removed
              * In a website context, every asset from another website
        """
        current_website = self.env['website'].get_current_website(fallback=False)
        if not current_website:
            return self.filtered(lambda asset: not asset.website_id)

        most_specific_assets = self.env['ir.asset']
        for asset in self:
            if asset.website_id == current_website:
                # specific asset: add it if it's for the current website and ignore
                # it if it's for another website
                most_specific_assets += asset
            elif not asset.website_id:
                # no key: added either way
                if not asset.key:
                    most_specific_assets += asset
                # generic asset: add it iff for the current website, there is no
                # specific asset for this asset (based on the same `key` attribute)
                elif not any(asset.key == asset2.key and asset2.website_id == current_website for asset2 in self):
                    most_specific_assets += asset

        return most_specific_assets

    def write(self, vals):
        """COW for ir.asset. This way editing websites does not impact other
        websites. Also this way newly created websites will only
        contain the default assets.
        """
        current_website_id = self.env.context.get('website_id')
        if not current_website_id or self.env.context.get('no_cow'):
            return super().write(vals)

        for asset in self.with_context(active_test=False):
            # No need of COW if the asset is already specific
            if asset.website_id:
                super(IrAsset, asset).write(vals)
                continue

            # If already a specific asset for this generic asset, write on it
            website_specific_asset = asset.search([
                ('key', '=', asset.key),
                ('website_id', '=', current_website_id)
            ], limit=1)
            if website_specific_asset:
                super(IrAsset, website_specific_asset).write(vals)
                continue

            copy_vals = {'website_id': current_website_id, 'key': asset.key}
            website_specific_asset = asset.copy(copy_vals)

            super(IrAsset, website_specific_asset).write(vals)

        return True
