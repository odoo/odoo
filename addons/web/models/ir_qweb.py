# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
from collections import OrderedDict

from odoo import api, models
from odoo.tools import pycompat
from odoo.tools import html_escape as escape


class Image(models.AbstractModel):
    """
    Widget options:

    ``class``
        set as attribute on the generated <img> tag
    """
    _name = 'ir.qweb.field.image'
    _description = 'Qweb Field Image'
    _inherit = 'ir.qweb.field.image'

    @api.model
    def record_to_html(self, record, field_name, options):
        assert options['tagName'] != 'img',\
            "Oddly enough, the root tag of an image field can not be img. " \
            "That is because the image goes into the tag, or it gets the " \
            "hose again."

        if options.get('qweb_img_raw_data', False):
            return super(Image, self).record_to_html(record, field_name, options)

        aclasses = ['img', 'img-fluid'] if options.get('qweb_img_responsive', True) else ['img']
        aclasses += options.get('class', '').split()
        classes = ' '.join(pycompat.imap(escape, aclasses))

        max_size = None
        if options.get('resize'):
            max_size = options.get('resize')
        else:
            max_width, max_height = options.get('max_width', 0), options.get('max_height', 0)
            if max_width or max_height:
                max_size = '%sx%s' % (max_width, max_height)

        sha = hashlib.sha1(str(getattr(record, '__last_update')).encode('utf-8')).hexdigest()[0:7]
        max_size = '' if max_size is None else '/%s' % max_size
        avoid_if_small = '&avoid_if_small=true' if options.get('avoid_if_small') else ''
        src = '/web/image/%s/%s/%s%s?unique=%s%s' % (record._name, record.id, field_name, max_size, sha, avoid_if_small)

        alt = None
        if options.get('alt-field') and getattr(record, options['alt-field'], None):
            alt = escape(record[options['alt-field']])
        elif options.get('alt'):
            alt = options['alt']

        src_zoom = None
        if options.get('zoom') and getattr(record, options['zoom'], None):
            src_zoom = '/web/image/%s/%s/%s%s?unique=%s' % (record._name, record.id, options['zoom'], max_size, sha)
        elif options.get('zoom'):
            src_zoom = options['zoom']

        itemprop = None
        if options.get('itemprop'):
            itemprop = options['itemprop']

        atts = OrderedDict()
        atts["src"] = src
        atts["itemprop"] = itemprop
        atts["class"] = classes
        atts["style"] = options.get('style')
        atts["alt"] = alt
        atts["data-zoom"] = src_zoom and u'1' or None
        atts["data-zoom-image"] = src_zoom
        atts["data-no-post-process"] = options.get('data-no-post-process')

        atts = self.env['ir.qweb']._post_processing_att('img', atts, options.get('template_options'))

        img = ['<img']
        for name, value in atts.items():
            if value:
                img.append(' ')
                img.append(escape(pycompat.to_text(name)))
                img.append('="')
                img.append(escape(pycompat.to_text(value)))
                img.append('"')
        img.append('/>')

        return u''.join(img)
