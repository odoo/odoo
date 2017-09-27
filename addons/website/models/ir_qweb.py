# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import models
from odoo.http import request


class QWeb(models.AbstractModel):
    """ QWeb object for rendering stuff in the website context """

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

    def _get_asset(self, xmlid, options, css=True, js=True, debug=False, async=False, values=None):
        website = getattr(request, 'website', None) if request else None
        if website and website.cdn_activated:
            values = dict(values, url_for=website.get_cdn_url)
        return super(QWeb, self)._get_asset(xmlid, options, css, js, debug, async, values)

    def _website_build_attribute(self, tagName, name, value, options, values):
        """ Compute the value of an attribute while rendering the template. """
        if name == self.URL_ATTRS.get(tagName) and values.get('url_for'):
            return values.get('url_for')(value or '')
        elif request and getattr(request, 'website', None) and request.website.cdn_activated and (name == self.URL_ATTRS.get(tagName) or name == self.CDN_TRIGGERS.get(tagName)):
            return request.website.get_cdn_url(value or '')
        return value

    def _wrap_build_attributes(self, el, items, options):
        """ Map items corresponding to URL and CDN attributes to an ast expression. """
        if options.get('rendering_bundle'):
            return items

        url_att = self.URL_ATTRS.get(el.tag)
        cdn_att = self.CDN_TRIGGERS.get(el.tag)

        def process(item):
            if isinstance(item, tuple) and (item[0] in (url_att, cdn_att)):
                return (item[0], ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_website_build_attribute',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Str(el.tag),
                        ast.Str(item[0]),
                        item[1],
                        ast.Name(id='options', ctx=ast.Load()),
                        ast.Name(id='values', ctx=ast.Load()),
                    ], keywords=[],
                    starargs=None, kwargs=None
                ))
            else:
                return item

        return [process(it) for it in items]

    def _compile_static_attributes(self, el, options):
        items = super(QWeb, self)._compile_static_attributes(el, options)
        return self._wrap_build_attributes(el, items, options)

    def _compile_dynamic_attributes(self, el, options):
        items = super(QWeb, self)._compile_dynamic_attributes(el, options)
        return self._wrap_build_attributes(el, items, options)

    # method called by computing code

    def _get_dynamic_att(self, tagName, atts, options, values):
        atts = super(QWeb, self)._get_dynamic_att(tagName, atts, options, values)
        if options.get('rendering_bundle'):
            return atts
        for name, value in atts.items():
            atts[name] = self._website_build_attribute(tagName, name, value, options, values)
        return atts

    def _is_static_node(self, el):
        url_att = self.URL_ATTRS.get(el.tag)
        cdn_att = self.CDN_TRIGGERS.get(el.tag)
        return super(QWeb, self)._is_static_node(el) and \
                (not url_att or not el.get(url_att)) and \
                (not cdn_att or not el.get(cdn_att))
