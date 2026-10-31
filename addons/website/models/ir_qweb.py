# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from collections import OrderedDict
from datetime import timezone

from odoo import models
from odoo.http import request
from odoo.addons.website.tools import (
    add_form_signature,
    get_next_visibility_change,
    is_in_datetime_range,
    parse_visibility_timestamp,
)


re_background_image = re.compile(r"(background-image\s*:\s*url\(\s*['\"]?\s*)([^)'\"]+)")
re_translate_span = re.compile(r'<span.+?data-oe-translation-source-sha.+?>(.+?)</span>')


class IrQweb(models.AbstractModel):
    """ IrQweb object for rendering stuff in the website context """

    _inherit = 'ir.qweb'

    URL_ATTRS = {
        'form': 'action',
        'a': 'href',
        'link': 'href',
        'script': 'src',
        'img': 'src',
    }

    def _compile_root(self, element, compile_context):
        # Removes the attributes used by the "/website/snippet/filter_templates"
        # controller and used only to be filtered without using irQweb rendering
        if not self._is_static_node(element, compile_context):
            for data_filter in [
                    'data-number-of-elements', 'data-number-of-elements-sm',
                    'data-number-of-elements-fetch', 'data-row-per-slide',
                    'data-arrow-position', 'data-extra-classes',
                    'data-extra-snippet-classes', 'data-container-classes',
                    'data-content-classes', 'data-column-classes', 'data-thumb',
                ]:
                element.attrib.pop(data_filter, None)
        return super()._compile_root(element, compile_context)

    def _get_template(self, template):
        element, document, ref = super()._get_template(template)
        if self.env.context.get('website_id'):
            add_form_signature(element, self.sudo().env)
        return element, document, ref

    # assume cache will be invalidated by third party on write to ir.ui.view
    def _get_template_cache_keys(self):
        """ Return the list of context keys to use for caching ``_compile``. """
        return super()._get_template_cache_keys() + ['website_id', 'cookies_allowed', 'rendering_bundle']

    def _pre_processing_att(self, attrib):
        self._copy_translate_attributes(attrib)
        super()._pre_processing_att(attrib)

    def _copy_translate_attributes(self, atts):
        """
        In translation mode, store `***.translate` attributes into a sibling
        attribute `data-oe-translate-***`. This is necessary for attributes that
        expect a value in a specific format (e.g. `src` which needs a URL) and
        cannot keep the translation span (see `translate_func`) in the HTML
        output. Other attributes can also take advantage of it.
        """
        if self.env.website and self.env.context.get('edit_translations'):
            for att, value in list(atts.items()):
                if att.endswith('.translate'):
                    match = re.search(re_translate_span, value)
                    if match:
                        atts['data-oe-translate-{}'.format(att.removesuffix('.translate'))] = value
                        atts[att] = match.group(1)

    def _post_processing_att(self, tagName, atts):
        if atts.get('data-no-post-process'):
            return atts

        atts = super()._post_processing_att(tagName, atts)

        website = self.env.website
        if website and tagName == 'img' and 'loading' not in atts:
            atts['loading'] = 'lazy'  # default is auto

        if self.env.context.get('inherit_branding') or self.env.context.get('rendering_bundle') or \
           self.env.context.get('edit_translations') or self.env.context.get('debug') or (request and request.session.debug):
            return atts

        if not website:
            return atts

        if website._should_remove_third_party_trackers():
            website._remove_third_party_trackers(tagName, atts, ['domains', 'classes'])

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

    def _get_visibility_now(self):
        """ Return the current time as a POSIX timestamp in seconds.
        We use cr.now() such that multiple checks in the same rendering process
        get the same time. """
        return self.env.cr.now().replace(tzinfo=timezone.utc).timestamp()

    def _check_datetime_visibility(self, visible_from, visible_until):
        """ Return True if the current time is in the given range. If a request
        is present, store the time of the closest future visibility change
        on `request.website_visibility_next_change`. This is used to determine
        for how long the page can be cached. """
        now = self._get_visibility_now()
        if request:
            next_change = get_next_visibility_change(now, visible_from, visible_until)
            known_next_change = getattr(request, 'website_visibility_next_change', None)
            if next_change and (not known_next_change or next_change < known_next_change):
                # A page could have different elements with their own visibility
                # ranges. We keep track of the closest change in the future.
                request.website_visibility_next_change = next_change
        return is_in_datetime_range(now, visible_from, visible_until)

    def _prepare_environment(self, values):
        irQweb = super()._prepare_environment(values)
        values['check_datetime_visibility'] = self._check_datetime_visibility
        return irQweb

    def _compile_node(self, el, compile_context, level):
        """ Add a `t-if` that calls `check_datetime_visibility` to
        conditionally-visible nodes that have `data-visibility-from` and/or
        `data-visibility-until`. Thus, the node is not in the HTML document
        when the current time is out of range, and the visitor cannot see it in
        the page source. The check occurs at render time, because the compiled
        view can be cached.

        Do not add the `t-if` when branding is active (edit mode or
        translation mode), because the user must be able to edit or translate
        the node. Also do not add the `t-if` when `rendering_bundle` is in
        context, which means that the view being compiled is a (custom) snippet
        not yet added to a page.

        Note that elements outside their visibility datetime range are always
        hidden outside edit / translation mode, see
        `hideOutOfDatetimeRangeElements`.

        The `data-visibility` attributes must be static.
        Trying to compile `t-att-...` or `t-attf-...` will produce an error.
        Dictionary forms (`t-att="{...}"`) can't be detected. In this case the
        node will silently leak into the page's HTML independently on branding
        and `hideOutOfDatetimeRangeElements` will hide it. """
        dynamic_atts = {
            f'{directive}-data-visibility{suffix}'
            for directive in ('t-att', 't-attf')
            for suffix in ('-from', '-until')
        }
        if dynamic_atts & set(el.attrib.keys()):
            raise SyntaxError("A node cannot have a dynamic visibility or visibility datetime range")
        is_conditional = el.attrib.get("data-visibility") == "conditional"
        has_datetime_range = "data-visibility-from" in el.attrib or "data-visibility-until" in el.attrib
        if is_conditional and has_datetime_range:
            # Do this check also when branding is active, so that the same
            # template does not fail only for the visitors.
            if {'t-if', 't-elif', 't-else'} & set(el.attrib.keys()):
                raise SyntaxError("A node with a visibility datetime range cannot have t-if, t-elif or t-else directives")
            is_branded = (
                compile_context.get("inherit_branding") or
                compile_context.get("edit_translations") or
                self.env.context.get('rendering_bundle')
            )
            if not is_branded:
                visible_from = parse_visibility_timestamp(el.get('data-visibility-from'))
                visible_until = parse_visibility_timestamp(el.get('data-visibility-until'))
                el.set('t-if', f"check_datetime_visibility({visible_from!r}, {visible_until!r})")
        return super()._compile_node(el, compile_context, level)
