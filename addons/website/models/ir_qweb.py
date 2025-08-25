# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import logging

from collections import OrderedDict
from urllib3.util import parse_url

from odoo import models
from odoo.http import request
from odoo.tools import lazy
from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.osv import expression
from odoo.addons.website.models import ir_http
from odoo.exceptions import AccessError


_logger = logging.getLogger(__name__)
re_background_image = re.compile(r"(background-image\s*:\s*url\(\s*['\"]?\s*)([^)'\"]+)")


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
        return super()._get_template_cache_keys() + ['website_id', 'cookies_allowed']

    def _prepare_frontend_environment(self, values):
        """ Update the values and context with website specific value
            (required to render website layout template)
        """
        irQweb = super()._prepare_frontend_environment(values)

        current_website = request.website
        editable = has_group_designer = irQweb.env.user.has_group('website.group_website_designer')
        has_group_restricted_editor = irQweb.env.user.has_group('website.group_website_restricted_editor')
        if not editable and has_group_restricted_editor and 'main_object' in values:
            try:
                main_object = values['main_object'].with_user(irQweb.env.user.id)
                current_website._check_user_can_modify(main_object)
                editable = True
            except AccessError:
                pass
        translatable = has_group_restricted_editor and irQweb.env.context.get('lang') != irQweb.env['ir.http']._get_default_lang().code
        editable = editable and not translatable

        if has_group_restricted_editor and irQweb.env.user.has_group('website.group_multi_website'):
            values['multi_website_websites_current'] = lazy(lambda: current_website.name)
            values['multi_website_websites'] = lazy(lambda: [
                {'website_id': website.id, 'name': website.name, 'domain': website.domain}
                for website in current_website.search([('id', '!=', current_website.id)])
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
            if 'main_object' in values and has_group_restricted_editor:
                func = getattr(values['main_object'], 'get_backend_menu_id', False)
                values['backend_menu_id'] = lazy(lambda: func and func() or irQweb.env['ir.model.data']._xmlid_to_res_id('website.menu_website_configuration'))

        # update options

        irQweb = irQweb.with_context(website_id=current_website.id)
        if 'inherit_branding' not in irQweb.env.context and not self.env.context.get('rendering_bundle'):
            if has_group_designer and editable:
                # in edit mode add branding on ir.ui.view tag nodes
                irQweb = irQweb.with_context(inherit_branding=True)
            elif has_group_restricted_editor:
                # will add the branding on fields (into values)
                irQweb = irQweb.with_context(inherit_branding_auto=True)

        # Avoid cache inconsistencies: if the cookies have been accepted, the
        # DOM structure should reflect it after a reload and not be stuck in its
        # previous state (see the part related to cookies in
        # `_post_processing_att`).
        is_allowed_optional_cookies = request.env['ir.http']._is_allowed_cookie('optional')
        irQweb = irQweb.with_context(cookies_allowed=is_allowed_optional_cookies)

        return irQweb

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

        if (
            website.cookies_bar
            and website.block_third_party_domains
            and not self.env.context.get('cookies_allowed')
            and not request.env.user.has_group('website.group_website_restricted_editor')
        ):
            # If the cookie banner is activated, 3rd-party embedded iframes and
            # scripts should be controlled. As such:
            # - 'domains' is a watchlist on the iframe/script's src itself,
            # - 'classes' is a watchlist on container elements in which iframes
            # are/could be built on the fly client-side for some reason.
            cookies_watchlist = {
                'domains': website.blocked_third_party_domains.split('\n'),
                'classes': website._get_blocked_iframe_containers_classes(),
            }
            remove_src = False
            if tagName in ('iframe', 'script'):
                src_host = parse_url((atts.get('src') or '').lower()).host
                if src_host:
                    remove_src = any(
                        # "www.example.com" and "example.com" should block both.
                        src_host == domain.removeprefix('www.')
                        # "domain.com" should block "subdomain.domain.com", but
                        # not "(subdomain.)mydomain.com".
                        or src_host.endswith('.' + domain.removeprefix('www.'))
                        for domain in cookies_watchlist['domains']
                    )
            if (
                remove_src
                or cookies_watchlist['classes'].intersection((atts.get('class') or '').split(' '))
            ):
                atts['data-need-cookies-approval'] = 'true'
                # Case class in watchlist: we stop here. The element could
                # contain an iframe created on the fly client-side. It is marked
                # now so that the iframe can be marked later when created.
                # Case iframe/script's src in watchlist: we adapt the src.
                if 'src' in atts:
                    atts['data-nocookie-src'] = atts['src']
                    atts['src'] = 'about:blank'

        name = self.URL_ATTRS.get(tagName)
        if request:
            value = atts.get(name) if name else None
            if value not in (None, False, ()):
                atts[name] = self.env['ir.http']._url_for(str(value))

            # Adapt background-image URL in the same way as image src.
            atts = self._adapt_style_background_image(atts, self.env['ir.http']._url_for)

        if not website.cdn_activated:
            return atts

        data_name = f'data-{name}'
        if name and (name in atts or data_name in atts):
            atts = OrderedDict(atts)
            if name in atts and atts[name] not in (False, None, ()):
                atts[name] = website.get_cdn_url(atts[name])
            if data_name in atts and atts[data_name] not in (False, None, ()):
                atts[data_name] = website.get_cdn_url(atts[data_name])
        atts = self._adapt_style_background_image(atts, website.get_cdn_url)

        return atts

    def _adapt_style_background_image(self, atts, url_adapter):
        if isinstance(atts.get('style'), str) and 'background-image' in atts['style']:
            atts['style'] = re_background_image.sub(lambda m: '%s%s' % (m[1], url_adapter(m[2])), atts['style'])
        return atts

    def _get_bundles_to_pregenarate(self):
        js_assets, css_assets = super(IrQWeb, self)._get_bundles_to_pregenarate()
        assets = {
            'website.backend_assets_all_wysiwyg',
            'website.assets_all_wysiwyg_inside',
        }
        return (js_assets | assets, css_assets | assets)
