# -*- coding: utf-8 -*-
from openerp.addons.web.http import request
from openerp.osv import orm


class QWeb(orm.AbstractModel):
    """ QWeb object for rendering stuff in the website context
    """
    _inherit = 'ir.qweb'

    URL_ATTRS = {
        'form': 'action',
        'a': 'href',
    }

    CDN_TRIGGERS = {
        'link':    'href',
        'script':  'src',
        'img':     'src',
    }

    PRESERVE_WHITESPACE = [
        'pre',
        'textarea',
        'script',
        'style',
    ]

    def render_attribute(self, element, name, value, qwebcontext):
        context = qwebcontext.context or {}
        if not context.get('rendering_bundle'):
            if name == self.URL_ATTRS.get(element.tag) and qwebcontext.get('url_for'):
                value = qwebcontext.get('url_for')(value)
            elif request and getattr(request, 'website', None) and request.website.cdn_activated and (name == self.URL_ATTRS.get(element.tag) or name == self.CDN_TRIGGERS.get(element.tag)):
                value = request.website.get_cdn_url(value)
        return super(QWeb, self).render_attribute(element, name, value, qwebcontext)

    def render_text(self, text, element, qwebcontext):
        compress = request and not request.debug and getattr(request, 'website', None) and request.website.compress_html
        if compress and element.tag not in self.PRESERVE_WHITESPACE:
            text = self.re_remove_spaces.sub(' ', text)
        return super(QWeb, self).render_text(text, element, qwebcontext)

    def render_tail(self, tail, element, qwebcontext):
        compress = request and not request.debug and getattr(request, 'website', None) and request.website.compress_html
        if compress and element.getparent().tag not in self.PRESERVE_WHITESPACE:
            # No need to recurse because those tags children are not html5 parser friendly
            tail = self.re_remove_spaces.sub(' ', tail)
        return super(QWeb, self).render_tail(tail, element, qwebcontext)
