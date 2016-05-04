# -*- coding: utf-8 -*-
from openerp.addons.web.http import request
from openerp.osv import orm
import ast


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

    def _website_build_attribute(self, tagName, name, value, qwebcontext):
        context = qwebcontext.env.context or {}
        if not context.get('rendering_bundle'):
            if name == self.URL_ATTRS.get(tagName) and qwebcontext.get('url_for'):
                return qwebcontext.get('url_for')(value or '')
            elif request and request.website and request.website.cdn_activated and (name == self.URL_ATTRS.get(tagName) or name == self.CDN_TRIGGERS.get(tagName)):
                return request.website.get_cdn_url(value or '')
        return value

    def _wrap_build_attributes(self, el, items):
        url_att = self.URL_ATTRS.get(el.tag)
        cdn_att = self.CDN_TRIGGERS.get(el.tag)
        for item in items:
            if isinstance(item, tuple) and (item[0] == url_att or item[0] == cdn_att):
                items[items.index(item)] = (item[0], ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_website_build_attribute',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Str(el.tag),
                        ast.Str(item[0]),
                        item[1],
                        ast.Name(id='qwebcontext', ctx=ast.Load()),
                    ], keywords=[],
                    starargs=None, kwargs=None
                ))
        return items

    def _serialize_static_attributes(self, el):
        items = super(QWeb, self)._serialize_static_attributes(el)
        return self._wrap_build_attributes(el, items)

    def _compile_dynamic_attributes(self, el):
        items = super(QWeb, self)._compile_dynamic_attributes(el)
        return self._wrap_build_attributes(el, items)

    def _compile_dynamic_att(self, tagName, atts, qwebcontext):
        atts = super(QWeb, self)._compile_dynamic_att(tagName, atts, qwebcontext)
        for name, value in atts.iteritems():
            atts[name] = self.build_attribute(tagName, name, value, qwebcontext)
        return atts
