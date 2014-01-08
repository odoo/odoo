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

import werkzeug.utils
from dateutil import parser
from lxml import etree, html
from PIL import Image as I
import openerp.modules

import openerp
from openerp.osv import orm, fields
from openerp.tools import ustr, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
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
        if options is None: options = {}
        column = record._model._all_columns[field_name].column
        attrs = [('data-oe-translate', 1 if column.translate else 0)]

        placeholder = options.get('placeholder') \
                   or source_element.getAttribute('placeholder') \
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
        column = record._model._all_columns[field_name].column
        value = record[field_name]
        if isinstance(value, basestring):
            value = datetime.datetime.strptime(
                value, DEFAULT_SERVER_DATETIME_FORMAT)
        if value:
            value = column.context_timestamp(
                cr, uid, timestamp=value, context=context)
            value = value.strftime(openerp.tools.DEFAULT_SERVER_DATETIME_FORMAT)

        attrs = super(DateTime, self).attributes(
            cr, uid, field_name, record, options, source_element, g_att, t_att,
            qweb_context, context=None)
        return itertools.chain(attrs, [
            ('data-oe-original', value)
        ])

    def from_html(self, cr, uid, model, column, element, context=None):
        value = element.text_content().strip()
        if not value: return False

        datetime.datetime.strptime(value, DEFAULT_SERVER_DATETIME_FORMAT)
        return value

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
        # FIXME: layering violations all the things
        Model = self.pool[element.get('data-oe-model')]
        M2O = self.pool[column._obj]
        field = element.get('data-oe-field')
        id = int(element.get('data-oe-id'))
        value = element.text_content().strip()

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
        assert source_element.nodeName != 'img',\
            "Oddly enough, the root tag of an image field can not be img. " \
            "That is because the image goes into the tag, or it gets the " \
            "hose again."

        return super(Image, self).to_html(
            cr, uid, field_name, record, options,
            source_element, t_att, g_att, qweb_context, context=context)

    def record_to_html(self, cr, uid, field_name, record, column, options=None, context=None):
        if options is None: options = {}
        classes = ['img', 'img-responsive'] + options.get('class', '').split()

        return ir_qweb.HTMLSafe('<img class="%s" src="/website/image?model=%s&field=%s&id=%s"/>' % (
            ' '.join(itertools.imap(werkzeug.utils.escape, classes)),
            record._model._name,
            field_name, record.id))

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
    _inherit = ['website.qweb.field', 'website.qweb.field.many2one']

    def from_html(self, cr, uid, model, column, element, context=None):
        # FIXME: this behavior is really weird, what if the user wanted to edit the name of the related thingy? Should m2os really be editable without a widget?
        divs = element.xpath(".//div")
        for div in divs:
            if div != divs[0]:
                div.getparent().remove(div)
        return super(Contact, self).from_html(cr, uid, model, column, element, context=context)

    def record_to_html(self, cr, uid, field_name, record, column, options=None, context=None):
        opf = options.get('fields') or ["name", "address", "phone", "mobile", "fax", "email"]

        if not getattr(record, field_name):
            return None

        id = getattr(record, field_name).id
        field_browse = self.pool[column._obj].browse(cr, openerp.SUPERUSER_ID, id, context={"show_address": True})
        value = werkzeug.utils.escape( field_browse.name_get()[0][1] )

        IMD = self.pool["ir.model.data"]
        model, id = IMD.get_object_reference(cr, uid, "website", "contact")
        view = self.pool["ir.ui.view"].browse(cr, uid, id, context=context)

        html = view.render({
            'name': value.split("\n")[0],
            'address': werkzeug.utils.escape("\n".join(value.split("\n")[1:])),
            'phone': field_browse.phone,
            'mobile': field_browse.mobile,
            'fax': field_browse.fax,
            'email': field_browse.email,
            'fields': opf,
            'options': options
        }, engine='website.qweb', context=context)

        return ir_qweb.HTMLSafe(html)
