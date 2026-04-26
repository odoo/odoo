# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.fields import Domain


class IrAsset(models.Model):
    _inherit = 'ir.asset'

    key = fields.Char(copy=False) # used to resolve multiple assets in a multi-website environment
    website_id = fields.Many2one('website', ondelete='cascade')

    active_draft = fields.Integer(
        string='Draft Active State',
        default=-1,
        help='Stores the active state for this view in the draft mode, equals to -1 if it\'s equal to the "active" field.')

    def _get_asset_params(self):
        params = super()._get_asset_params()
        params['website_id'] = self.env['website'].get_current_website(fallback=False).id
        params['draft_preview'] = bool(self.env.context.get('draft_preview'))
        return params

    def _get_asset_bundle_url(self, filename, unique, assets_params, ignore_params=False):
        route_prefix = '/web/assets'
        if ignore_params: # we dont care about website id, match both
            route_prefix = '/web/assets%'
        elif website_id := assets_params.get('website_id', None):
            if assets_params.get('draft_preview'):
                route_prefix = f'/web/assets/{website_id}/draft'
            else:
                route_prefix = f'/web/assets/{website_id}'
        return f'{route_prefix}/{unique}/{filename}'

    def _get_related_assets(self, domain, *, website_id=None, draft_preview=False, **params):
        if website_id:
            domain = Domain(domain) & self.env['website'].browse(website_id).website_domain()
        assets = super()._get_related_assets(domain, **params)
        assets = assets.filter_duplicate(website_id)
        if draft_preview:
            assets = self._prefer_draft_assets(assets)
        else:
            assets = assets.filtered(lambda a: not (a.path and a.path.startswith('/_custom_draft/')))
        return assets

    def _prefer_draft_assets(self, assets):
        """When in draft_preview mode, swap any non-draft custom asset for its
        _draft counterpart if it exists.
        """
        draft_targets = set()
        for asset in assets:
            if asset.path and asset.path.startswith('/_custom_draft/'):
                draft_targets.add(asset.target)

        if not draft_targets:
            return assets

        def _keep(asset):
            return not (asset.path and asset.path.startswith('/_custom/') and asset.target in draft_targets)

        return assets.filtered(_keep)

    def _get_active_addons_list(self, *, website_id=None, **params):
        """Overridden to discard inactive themes."""
        addons_list = super()._get_active_addons_list(**params)

        if not website_id:
            return addons_list

        IrModule = self.env['ir.module.module'].sudo()
        # discard all theme modules except website.theme_id
        themes = IrModule.search(IrModule.get_themes_domain()) - self.env["website"].browse(website_id).theme_id
        to_remove = set(themes.mapped('name'))

        return [name for name in addons_list if name not in to_remove]

    def filter_duplicate(self, website_id=None):
        """ Filter current recordset only keeping the most suitable asset per distinct name.
            Every non-accessible asset will be removed from the set:

              * In non website context, every asset with a website will be removed
              * In a website context, every asset from another website
        """
        if website_id is None:
            website_id = self.env['website'].get_current_website(fallback=False).id
        if not website_id:
            return self.filtered(lambda asset: not asset.website_id)

        specific_asset_keys = {asset.key for asset in self if asset.website_id.id == website_id and asset.key}
        most_specific_assets = []
        for asset in self:
            if asset.website_id:
                # specific asset: add it if it's for the current website and ignore
                # it if it's for another website
                if asset.website_id.id == website_id:
                    most_specific_assets.append(asset)
                continue
            elif not asset.key:
                # no key: added either way
                most_specific_assets.append(asset)
            elif asset.key not in specific_asset_keys:
                # generic asset: add it iff for the current website, there is no
                # specific asset for this asset (based on the same `key` attribute)
                most_specific_assets.append(asset)

        return self.browse().union(most_specific_assets)

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

    def set_active_draft(self, enable):
        """ Store the active state for draft mode

        :param bool enable: True to mark assets as active in draft, False to mark
            them as inactive in draft.
        """
        self.write({'active_draft': int(enable)})

    def apply_active_draft(self):
        """ Copy the draft value into active and reset the draft"""
        for record in self.filtered(lambda r: r.active_draft != -1):
            record.write({
                'active': record.active_draft,
                'active_draft': -1,
            })

    def delete_active_draft(self):
        """ Delete the active draft state """
        for record in self.filtered(lambda r: r.active_draft != -1):
            record.write({
                'active_draft': -1,
            })
