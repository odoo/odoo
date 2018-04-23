# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from collections import OrderedDict

from odoo import models
from odoo.http import request


re_background_image = re.compile(r"(background-image\s*:\s*url\(\s*['\"]?\s*)([^)'\"]+)")


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
        if isinstance(atts.get('style'), str) and 'background-image' in atts['style']:
            atts = OrderedDict(atts)
            atts['style'] = re_background_image.sub(lambda m: '%s%s' % (m.group(1), website.get_cdn_url(m.group(2))), atts['style'])

        return atts
