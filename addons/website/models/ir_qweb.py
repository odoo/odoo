# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import OrderedDict

from odoo import models
from odoo.http import request


class QWeb(models.AbstractModel):
    """ QWeb object for rendering stuff in the website context """

    _inherit = 'ir.qweb'

    URL_ATTRS = {
        'form':   'action',
        'a':      'href',
        'link':   'href',
        'script': 'src',
        'img':    'src',
    }

    def _post_processing_att(self, tagName, atts, options):
        if atts.get('data-no-post-process'):
            return atts

        atts = super(QWeb, self)._post_processing_att(tagName, atts, options)

        if options.get('inherit_branding') or options.get('rendering_bundle') or \
           options.get('edit_translations') or options.get('debug') or (request and request.debug):
            return atts

        website = request and getattr(request, 'website', None)
        if not website and options.get('website_id'):
            website = self.env['website'].browse(options['website_id'])

        if not website or not website.cdn_activated:
            return atts

        name = self.URL_ATTRS.get(tagName)
        if name and name in atts:
            atts = OrderedDict(atts)
            atts[name] = website.get_cdn_url(atts[name])

        return atts
