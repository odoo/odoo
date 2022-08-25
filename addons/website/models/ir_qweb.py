# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from collections import OrderedDict

from odoo import models
from odoo.http import request
from odoo.tools import lazy
from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.addons.http_routing.models.ir_http import url_for
from odoo.osv import expression
from odoo.addons.website.models import ir_http

re_background_image = re.compile(r"(background-image\s*:\s*url\(\s*['\"]?\s*)([^)'\"]+)")


class AssetsBundleMultiWebsite(AssetsBundle):
    def _get_asset_url_values(self, id, unique, extra, name, sep, extension):
        website_id = self.env.context.get('website_id')
        website_id_path = website_id and ('%s/' % website_id) or ''
        extra = website_id_path + extra
        res = super(AssetsBundleMultiWebsite, self)._get_asset_url_values(id, unique, extra, name, sep, extension)
        return res

    def _get_assets_domain_for_already_processed_css(self, assets):
        res = super(AssetsBundleMultiWebsite, self)._get_assets_domain_for_already_processed_css(assets)
        current_website = self.env['website'].get_current_website(fallback=False)
        res = expression.AND([res, current_website.website_domain()])
        return res

    def get_debug_asset_url(self, extra='', name='%', extension='%'):
        website_id = self.env.context.get('website_id')
        website_id_path = website_id and ('%s/' % website_id) or ''
        extra = website_id_path + extra
        return super(AssetsBundleMultiWebsite, self).get_debug_asset_url(extra, name, extension)

class IrQWeb(models.AbstractModel):
    """ IrQWeb object for rendering stuff in the website context """

    _inherit = 'ir.qweb'

    URL_ATTRS = {
        'form': 'action',
        'a': 'href',
        'link': 'href',
        'script': 'src',
        'img': 'src',
    }

    # assume cache will be invalidated by third party on write to ir.ui.view
    def _get_template_cache_keys(self):
        """ Return the list of context keys to use for caching ``_compile``. """
        return super()._get_template_cache_keys() + ['website_id']

    def _prepare_frontend_environment(self, values):
        """ Update the values and context with website specific value
            (required to render website layout template)
        """
        irQweb = super()._prepare_frontend_environment(values)

        Website = irQweb.env['website']
        editable = request.website.is_publisher()
        translatable = editable and irQweb.env.context.get('lang') != irQweb.env['ir.http']._get_default_lang().code
        editable = editable and not translatable

        current_website = Website.get_current_website()

        has_group_publisher = irQweb.env.user.has_group('website.group_website_publisher')
        if has_group_publisher and irQweb.env.user.has_group('website.group_multi_website'):
            values['multi_website_websites_current'] = lazy(lambda: current_website.name)
            values['multi_website_websites'] = lazy(lambda: [
                {'website_id': website.id, 'name': website.name, 'domain': website.domain}
                for website in Website.search([('id', '!=', current_website.id)])
            ])

            cur_company = irQweb.env.company
            values['multi_website_companies_current'] = lazy(lambda: {'company_id': cur_company.id, 'name': cur_company.name})
            values['multi_website_companies'] = lazy(lambda: [
                {'company_id': comp.id, 'name': comp.name}
                for comp in irQweb.env.user.company_ids if comp != cur_company
            ])

        # update values

        values.update(dict(
            website=current_website,
            is_view_active=lazy(lambda: current_website.is_view_active),
            res_company=lazy(request.env['res.company'].browse(current_website._get_cached('company_id')).sudo),
            translatable=translatable,
            editable=editable,
        ))

        if editable:
            # form editable object, add the backend configuration link
            if 'main_object' in values and has_group_publisher:
                func = getattr(values['main_object'], 'get_backend_menu_id', False)
                values['backend_menu_id'] = lazy(lambda: func and func() or irQweb.env['ir.model.data']._xmlid_to_res_id('website.menu_website_configuration'))

        # update options

        irQweb = irQweb.with_context(website_id=current_website.id)

        if 'inherit_branding' not in irQweb.env.context and not self.env.context.get('rendering_bundle'):
            if editable:
                # in edit mode add brancding on ir.ui.view tag nodes
                irQweb = irQweb.with_context(inherit_branding=True)
            elif has_group_publisher and not translatable:
                # will add the branding on fields (into values)
                irQweb = irQweb.with_context(inherit_branding_auto=True)

        return irQweb

    def _get_asset_bundle(self, xmlid, files, env=None, css=True, js=True):
        return AssetsBundleMultiWebsite(xmlid, files, env=env)

    def _post_processing_att(self, tagName, atts):
        if atts.get('data-no-post-process'):
            return atts

        atts = super()._post_processing_att(tagName, atts)

        website = ir_http.get_request_website()
        if not website and self.env.context.get('website_id'):
            website = self.env['website'].browse(self.env.context['website_id'])
        if website and tagName == 'img' and 'loading' not in atts:
            atts['loading'] = 'lazy'  # default is auto

        if self.env.context.get('inherit_branding') or self.env.context.get('rendering_bundle') or \
           self.env.context.get('edit_translations') or self.env.context.get('debug') or (request and request.session.debug):
            return atts

        if not website:
            return atts

        name = self.URL_ATTRS.get(tagName)
        if request and name and name in atts:
            atts[name] = url_for(atts[name])

        if not website.cdn_activated:
            return atts

        data_name = f'data-{name}'
        if name and (name in atts or data_name in atts):
            atts = OrderedDict(atts)
            if name in atts:
                atts[name] = website.get_cdn_url(atts[name])
            if data_name in atts:
                atts[data_name] = website.get_cdn_url(atts[data_name])
        if isinstance(atts.get('style'), str) and 'background-image' in atts['style']:
            atts = OrderedDict(atts)
            atts['style'] = re_background_image.sub(lambda m: '%s%s' % (m.group(1), website.get_cdn_url(m.group(2))), atts['style'])

        return atts
