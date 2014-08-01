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
import os
import urllib2
import urlparse
import re

import pytz
import werkzeug.urls
import werkzeug.utils
from dateutil import parser
from lxml import etree, html
from PIL import Image as I
import openerp.modules

import openerp
from openerp.osv import orm, fields
from openerp.tools import ustr, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import html_escape as escape
from openerp.addons.web.http import request
from openerp.addons.base.ir import ir_qweb

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
    }

    def add_template(self, qcontext, name, node):
        # preprocessing for multilang static urls
        if request.website:
            for tag, attr in self.URL_ATTRS.iteritems():
                for e in node.iterdescendants(tag=tag):
                    url = e.get(attr)
                    if url:
                        e.set(attr, qcontext.get('url_for')(url))
        super(QWeb, self).add_template(qcontext, name, node)

    def render_att_att(self, element, attribute_name, attribute_value, qwebcontext):
        att, val = super(QWeb, self).render_att_att(element, attribute_name, attribute_value, qwebcontext)

        if request.website and att == self.URL_ATTRS.get(element.tag) and isinstance(val, basestring):
            val = qwebcontext.get('url_for')(val)
        return att, val

    def get_converter_for(self, field_type):
        return self.pool.get(
            'website.qweb.field.' + field_type,
            self.pool['website.qweb.field'])

class Field(orm.AbstractModel):
    _name = 'website.qweb.field'
    _inherit = 'ir.qweb.field'

    def attributes(self, cr, uid, field_name, record, options,
                   source_element, g_att, t_att, qweb_context, context=None):
        if options is None: options = {}
        column = record._model._all_columns[field_name].column
        attrs = [('data-oe-translate', 1 if column.translate else 0)]

        placeholder = options.get('placeholder') \
                   or source_element.get('placeholder') \
                   or getattr(column, 'placeholder', None)
        if placeholder:
            attrs.append(('placeholder', placeholder))

        return itertools.chain(
            super(Field, self).attributes(cr, uid, field_name, record, options,
                                          source_element, g_att, t_att,
                                          qweb_context, context=context),
            attrs
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

    def attributes(self, cr, uid, field_name, record, options,
                   source_element, g_att, t_att, qweb_context,
                   context=None):
        attrs = super(Date, self).attributes(
            cr, uid, field_name, record, options, source_element, g_att, t_att,
            qweb_context, context=None)
        return itertools.chain(attrs, [('data-oe-original', record[field_name])])

    def from_html(self, cr, uid, model, column, element, context=None):
        value = element.text_content().strip()
        if not value: return False

        datetime.datetime.strptime(value, DEFAULT_SERVER_DATE_FORMAT)
        return value

class DateTime(orm.AbstractModel):
    _name = 'website.qweb.field.datetime'
    _inherit = ['website.qweb.field', 'ir.qweb.field.datetime']

    def attributes(self, cr, uid, field_name, record, options,
                   source_element, g_att, t_att, qweb_context,
                   context=None):
        value = record[field_name]
        if isinstance(value, basestring):
            value = datetime.datetime.strptime(
                value, DEFAULT_SERVER_DATETIME_FORMAT)
        if value:
            # convert from UTC (server timezone) to user timezone
            value = fields.datetime.context_timestamp(
                cr, uid, timestamp=value, context=context)
            value = value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        attrs = super(DateTime, self).attributes(
            cr, uid, field_name, record, options, source_element, g_att, t_att,
            qweb_context, context=None)
        return itertools.chain(attrs, [
            ('data-oe-original', value)
        ])

    def from_html(self, cr, uid, model, column, element, context=None):
        if context is None: context = {}
        value = element.text_content().strip()
        if not value: return False

        # parse from string to datetime
        dt = datetime.datetime.strptime(value, DEFAULT_SERVER_DATETIME_FORMAT)

        # convert back from user's timezone to UTC
        tz_name = context.get('tz') \
            or self.pool['res.users'].read(cr, openerp.SUPERUSER_ID, uid, ['tz'], context=context)['tz']
        if tz_name:
            try:
                user_tz = pytz.timezone(tz_name)
                utc = pytz.utc

                dt = user_tz.localize(dt).astimezone(utc)
            except Exception:
                logger.warn(
                    "Failed to convert the value for a field of the model"
                    " %s back from the user's timezone (%s) to UTC",
                    model, tz_name,
                    exc_info=True)

        # format back to string
        return dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

class Text(orm.AbstractModel):
    _name = 'website.qweb.field.text'
    _inherit = ['website.qweb.field', 'ir.qweb.field.text']

    def from_html(self, cr, uid, model, column, element, context=None):
        return html_to_text(element)

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
        # FIXME: layering violations all the things
        Model = self.pool[element.get('data-oe-model')]
        M2O = self.pool[column._obj]
        field = element.get('data-oe-field')
        id = int(element.get('data-oe-id'))
        # FIXME: weird things are going to happen for char-type _rec_name
        value = html_to_text(element)

        # if anything blows up, just ignore it and bail
        try:
            # get parent record
            [obj] = Model.read(cr, uid, [id], [field])
            # get m2o record id
            (m2o_id, _) = obj[field]
            # assume _rec_name and write directly to it
            M2O.write(cr, uid, [m2o_id], {
                M2O._rec_name: value
            }, context=context)
        except:
            logger.exception("Could not save %r to m2o field %s of model %s",
                             value, field, Model._name)

        # not necessary, but might as well be explicit about it
        return None

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
        assert source_element.tag != 'img',\
            "Oddly enough, the root tag of an image field can not be img. " \
            "That is because the image goes into the tag, or it gets the " \
            "hose again."

        return super(Image, self).to_html(
            cr, uid, field_name, record, options,
            source_element, t_att, g_att, qweb_context, context=context)

    def record_to_html(self, cr, uid, field_name, record, column, options=None, context=None):
        if options is None: options = {}
        classes = ['img', 'img-responsive'] + options.get('class', '').split()

        url_params = {
            'model': record._model._name,
            'field': field_name,
            'id': record.id,
        }
        for options_key in ['max_width', 'max_height']:
            if options.get(options_key):
                url_params[options_key] = options[options_key]

        return ir_qweb.HTMLSafe('<img class="%s" src="/website/image?%s"/>' % (
            ' '.join(itertools.imap(escape, classes)),
            werkzeug.urls.url_encode(url_params)
        ))

    local_url_re = re.compile(r'^/(?P<module>[^]]+)/static/(?P<rest>.+)$')
    def from_html(self, cr, uid, model, column, element, context=None):
        url = element.find('img').get('src')

        url_object = urlparse.urlsplit(url)
        query = dict(urlparse.parse_qsl(url_object.query))
        if url_object.path == '/website/image':
            item = self.pool[query['model']].browse(
                cr, uid, int(query['id']), context=context)
            return item[query['field']]

        if self.local_url_re.match(url_object.path):
            return self.load_local_url(url)

        return self.load_remote_url(url)

    def load_local_url(self, url):
        match = self.local_url_re.match(urlparse.urlsplit(url).path)

        rest = match.group('rest')
        for sep in os.sep, os.altsep:
            if sep and sep != '/':
                rest.replace(sep, '/')

        path = openerp.modules.get_module_resource(
            match.group('module'), 'static', *(rest.split('/')))

        if not path:
            return None

        try:
            with open(path, 'rb') as f:
                # force complete image load to ensure it's valid image data
                image = I.open(f)
                image.load()
                f.seek(0)
                return f.read().encode('base64')
        except Exception:
            logger.exception("Failed to load local image %r", url)
            return None

    def load_remote_url(self, url):
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
            return None

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

class Duration(orm.AbstractModel):
    _name = 'website.qweb.field.duration'
    _inherit = [
        'ir.qweb.field.duration',
        'website.qweb.field.float',
    ]

    def attributes(self, cr, uid, field_name, record, options,
                   source_element, g_att, t_att, qweb_context,
                   context=None):
        attrs = super(Duration, self).attributes(
            cr, uid, field_name, record, options, source_element, g_att, t_att,
            qweb_context, context=None)
        return itertools.chain(attrs, [('data-oe-original', record[field_name])])

    def from_html(self, cr, uid, model, column, element, context=None):
        value = element.text_content().strip()

        # non-localized value
        return float(value)


class RelativeDatetime(orm.AbstractModel):
    _name = 'website.qweb.field.relative'
    _inherit = [
        'ir.qweb.field.relative',
        'website.qweb.field.datetime',
    ]

    # get formatting from ir.qweb.field.relative but edition/save from datetime


class Contact(orm.AbstractModel):
    _name = 'website.qweb.field.contact'
    _inherit = ['ir.qweb.field.contact', 'website.qweb.field.many2one']

class QwebView(orm.AbstractModel):
    _name = 'website.qweb.field.qweb'
    _inherit = ['ir.qweb.field.qweb']


def html_to_text(element):
    """ Converts HTML content with HTML-specified line breaks (br, p, div, ...)
    in roughly equivalent textual content.

    Used to replace and fixup the roundtripping of text and m2o: when using
    libxml 2.8.0 (but not 2.9.1) and parsing HTML with lxml.html.fromstring
    whitespace text nodes (text nodes composed *solely* of whitespace) are
    stripped out with no recourse, and fundamentally relying on newlines
    being in the text (e.g. inserted during user edition) is probably poor form
    anyway.

    -> this utility function collapses whitespace sequences and replaces
       nodes by roughly corresponding linebreaks
       * p are pre-and post-fixed by 2 newlines
       * br are replaced by a single newline
       * block-level elements not already mentioned are pre- and post-fixed by
         a single newline

    ought be somewhat similar (but much less high-tech) to aaronsw's html2text.
    the latter produces full-blown markdown, our text -> html converter only
    replaces newlines by <br> elements at this point so we're reverting that,
    and a few more newline-ish elements in case the user tried to add
    newlines/paragraphs into the text field

    :param element: lxml.html content
    :returns: corresponding pure-text output
    """

    # output is a list of str | int. Integers are padding requests (in minimum
    # number of newlines). When multiple padding requests, fold them into the
    # biggest one
    output = []
    _wrap(element, output)

    # remove any leading or tailing whitespace, replace sequences of
    # (whitespace)\n(whitespace) by a single newline, where (whitespace) is a
    # non-newline whitespace in this case
    return re.sub(
        r'[ \t\r\f]*\n[ \t\r\f]*',
        '\n',
        ''.join(_realize_padding(output)).strip())

_PADDED_BLOCK = set('p h1 h2 h3 h4 h5 h6'.split())
# https://developer.mozilla.org/en-US/docs/HTML/Block-level_elements minus p
_MISC_BLOCK = set((
    'address article aside audio blockquote canvas dd dl div figcaption figure'
    ' footer form header hgroup hr ol output pre section tfoot ul video'
).split())

def _collapse_whitespace(text):
    """ Collapses sequences of whitespace characters in ``text`` to a single
    space
    """
    return re.sub('\s+', ' ', text)
def _realize_padding(it):
    """ Fold and convert padding requests: integers in the output sequence are
    requests for at least n newlines of padding. Runs thereof can be collapsed
    into the largest requests and converted to newlines.
    """
    padding = None
    for item in it:
        if isinstance(item, int):
            padding = max(padding, item)
            continue

        if padding:
            yield '\n' * padding
            padding = None

        yield item
    # leftover padding irrelevant as the output will be stripped

def _wrap(element, output, wrapper=u''):
    """ Recursively extracts text from ``element`` (via _element_to_text), and
    wraps it all in ``wrapper``. Extracted text is added to ``output``

    :type wrapper: basestring | int
    """
    output.append(wrapper)
    if element.text:
        output.append(_collapse_whitespace(element.text))
    for child in element:
        _element_to_text(child, output)
    output.append(wrapper)

def _element_to_text(e, output):
    if e.tag == 'br':
        output.append(u'\n')
    elif e.tag in _PADDED_BLOCK:
        _wrap(e, output, 2)
    elif e.tag in _MISC_BLOCK:
        _wrap(e, output, 1)
    else:
        # inline
        _wrap(e, output)

    if e.tail:
        output.append(_collapse_whitespace(e.tail))
