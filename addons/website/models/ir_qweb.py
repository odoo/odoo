# -*- coding: utf-8 -*-
"""
Website-context rendering needs to add some metadata to rendered fields,
as well as render a few fields differently.

Also, adds methods to convert values back to openerp models.
"""

import cStringIO
import datetime
import itertools
import logging
import re
import urllib2
import urlparse

import werkzeug.utils
from dateutil import parser
from lxml import etree, html
from PIL import Image as I

from openerp.osv import orm, fields
from openerp.tools import ustr, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.web.http import request

REMOTE_CONNECTION_TIMEOUT = 2.5

logger = logging.getLogger(__name__)

class QWeb(orm.AbstractModel):
    """ QWeb object for rendering stuff in the website context
    """
    _name = 'website.qweb'
    _inherit = 'ir.qweb'

    URL_ATTRS = {
        'form': 'action',
        'a': 'href',
        'link': 'href',
        'frame': 'src',
        'iframe': 'src',
        'script': 'src',
    }

    def add_template(self, into, name, node, context):
        # preprocessing for multilang static urls
        if request and 'url_for' in context:
            router = request.httprequest.app.get_db_router(request.db).bind('')
            for tag, attr in self.URL_ATTRS.items():
                for e in node.getElementsByTagName(tag):
                    url = e.getAttribute(attr)
                    if url:
                        try:
                            func = router.match(url)[0]
                            if func.multilang:
                                e.setAttribute(attr, context['url_for'](url))
                        except Exception, e:
                            pass
        super(QWeb, self).add_template(into, name, node, context)

    def get_converter_for(self, field_type):
        return self.pool.get(
            'website.qweb.field.' + field_type,
            self.pool['website.qweb.field'])

class Field(orm.AbstractModel):
    _name = 'website.qweb.field'
    _inherit = 'ir.qweb.field'

    def attributes(self, cr, uid, field_name, record, options,
                   source_element, g_att, t_att, qweb_context, context=None):
        column = record._model._all_columns[field_name].column
        return itertools.chain(
            super(Field, self).attributes(cr, uid, field_name, record, options,
                                          source_element, g_att, t_att,
                                          qweb_context, context=context),
            [('data-oe-translate', 1 if column.translate else 0)]
        )

    def value_from_string(self, value):
        return value

    def from_html(self, cr, uid, model, column, element, context=None):
        return self.value_from_string(element.text_content().strip())

    def qweb_object(self):
        return self.pool['website.qweb']

class Integer(orm.AbstractModel):
    _name = 'website.qweb.field.integer'
    _inherit = ['website.qweb.field']

    value_from_string = int

class Float(orm.AbstractModel):
    _name = 'website.qweb.field.float'
    _inherit = ['website.qweb.field', 'ir.qweb.field.float']

    def from_html(self, cr, uid, model, column, element, context=None):
        lang = self.user_lang(cr, uid, context=context)

        value = element.text_content().strip()

        return float(value.replace(lang.thousands_sep, '')
                          .replace(lang.decimal_point, '.'))


def parse_fuzzy(in_format, value):
    day_first = in_format.find('%d') < in_format.find('%m')

    if '%y' in in_format:
        year_first = in_format.find('%y') < in_format.find('%d')
    else:
        year_first = in_format.find('%Y') < in_format.find('%d')

    return parser.parse(value, dayfirst=day_first, yearfirst=year_first)

class Date(orm.AbstractModel):
    _name = 'website.qweb.field.date'
    _inherit = ['website.qweb.field', 'ir.qweb.field.date']

    def from_html(self, cr, uid, model, column, element, context=None):
        lang = self.user_lang(cr, uid, context=context)
        in_format = lang.date_format.encode('utf-8')

        value = element.text_content().strip()
        try:
            dt = datetime.datetime.strptime(in_format, value)
        except ValueError:
            dt = parse_fuzzy(in_format, value)

        return dt.strftime(DEFAULT_SERVER_DATE_FORMAT)

class DateTime(orm.AbstractModel):
    _name = 'website.qweb.field.datetime'
    _inherit = ['website.qweb.field', 'ir.qweb.field.datetime']

    def from_html(self, cr, uid, model, column, element, context=None):
        lang = self.user_lang(cr, uid, context=context)
        in_format = (u"%s %s" % (lang.date_format, lang.time_format)).encode('utf-8')

        value = element.text_content().strip()
        try:
            dt = datetime.datetime.strptime(in_format, value)
        except ValueError:
            dt = parse_fuzzy(in_format, value)

        return dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

class Text(orm.AbstractModel):
    _name = 'website.qweb.field.text'
    _inherit = ['website.qweb.field', 'ir.qweb.field.text']

    def from_html(self, cr, uid, model, column, element, context=None):
        return element.text_content()

class Selection(orm.AbstractModel):
    _name = 'website.qweb.field.selection'
    _inherit = ['website.qweb.field', 'ir.qweb.field.selection']

    def from_html(self, cr, uid, model, column, element, context=None):
        value = element.text_content().strip()
        selection = column.reify(cr, uid, model, column, context=context)
        for k, v in selection:
            if isinstance(v, str):
                v = ustr(v)
            if value == v:
                return k

        raise ValueError(u"No value found for label %s in selection %s" % (
                         value, selection))

class ManyToOne(orm.AbstractModel):
    _name = 'website.qweb.field.many2one'
    _inherit = ['website.qweb.field', 'ir.qweb.field.many2one']

    def from_html(self, cr, uid, model, column, element, context=None):
        # FIXME: this behavior is really weird, what if the user wanted to edit the name of the related thingy? Should m2os really be editable without a widget?
        matches = self.pool[column._obj].name_search(
            cr, uid, name=element.text_content().strip(), context=context)
        # FIXME: no match? More than 1 match?
        assert len(matches) == 1
        return matches[0][0]

class HTML(orm.AbstractModel):
    _name = 'website.qweb.field.html'
    _inherit = ['website.qweb.field', 'ir.qweb.field.html']

    def from_html(self, cr, uid, model, column, element, context=None):
        content = []
        if element.text: content.append(element.text)
        content.extend(html.tostring(child)
                       for child in element.iterchildren(tag=etree.Element))
        return '\n'.join(content)


class Image(orm.AbstractModel):
    """
    Widget options:

    ``class``
        set as attribute on the generated <img> tag
    """
    _name = 'website.qweb.field.image'
    _inherit = ['website.qweb.field', 'ir.qweb.field.image']

    def to_html(self, cr, uid, field_name, record, options,
                source_element, t_att, g_att, qweb_context, context=None):
        assert source_element.nodeName != 'img',\
            "Oddly enough, the root tag of an image field can not be img. " \
            "That is because the image goes into the tag, or it gets the " \
            "hose again."

        return super(Image, self).to_html(
            cr, uid, field_name, record, options,
            source_element, t_att, g_att, qweb_context, context=context)

    def record_to_html(self, cr, uid, field_name, record, column, options=None, context=None):
        cls = ''
        if 'class' in options:
            cls = ' class="%s"' % werkzeug.utils.escape(options['class'])

        return '<img%s src="/website/image?model=%s&field=%s&id=%s"/>' % (
            cls, record._model._name, field_name, record.id)

    def from_html(self, cr, uid, model, column, element, context=None):
        url = element.find('img').get('src')

        url_object = urlparse.urlsplit(url)
        query = urlparse.parse_qs(url_object.query)
        if url_object.path == '/website/image' and query['model'] == 'ir.attachment':
            attachment = self.pool['ir.attachment'].browse(
                cr, uid, int(query['id']), context=context)
            return attachment.datas

        # remote URL?
        try:
            # should probably remove remote URLs entirely:
            # * in fields, downloading them without blowing up the server is a
            #   challenge
            # * in views, may trigger mixed content warnings if HTTPS CMS
            #   linking to HTTP images
            # implement drag & drop image upload to mitigate?

            req = urllib2.urlopen(url, timeout=REMOTE_CONNECTION_TIMEOUT)
            # PIL needs a seekable file-like image, urllib result is not seekable
            image = I.open(cStringIO.StringIO(req.read()))
            # force a complete load of the image data to validate it
            image.load()
        except Exception:
            logger.exception("Failed to load remote image %r", url)
            return False

        # don't use original data in case weird stuff was smuggled in, with
        # luck PIL will remove some of it?
        out = cStringIO.StringIO()
        image.save(out, image.format)
        return out.getvalue().encode('base64')

class Monetary(orm.AbstractModel):
    _name = 'website.qweb.field.monetary'
    _inherit = ['website.qweb.field', 'ir.qweb.field.monetary']

    def from_html(self, cr, uid, model, column, element, context=None):
        lang = self.user_lang(cr, uid, context=context)

        value = element.find('span').text.strip()

        return float(value.replace(lang.thousands_sep, '')
                          .replace(lang.decimal_point, '.'))
