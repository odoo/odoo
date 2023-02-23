# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
Web_editor-context rendering needs to add some metadata to rendered and allow to edit fields,
as well as render a few fields differently.

Also, adds methods to convert values back to Odoo models.
"""

import babel
import base64
import io
import json
import logging
import os
import re

import pytz
import requests
from datetime import datetime
from lxml import etree, html
from PIL import Image as I
from werkzeug import urls

import odoo.modules

from odoo import _, api, models, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tools import ustr, posix_to_ldml, pycompat
from odoo.tools import html_escape as escape
from odoo.tools.misc import get_lang, babel_locale_parse

REMOTE_CONNECTION_TIMEOUT = 2.5

logger = logging.getLogger(__name__)


class IrQWeb(models.AbstractModel):
    """ IrQWeb object for rendering editor stuff
    """
    _inherit = 'ir.qweb'

    def _compile_node(self, el, compile_context, indent):
        snippet_key = compile_context.get('snippet-key')
        if snippet_key == compile_context['template'] \
                or compile_context.get('snippet-sub-call-key') == compile_context['template']:
            # Get the path of element to only consider the first node of the
            # snippet template content (ignoring all ancestors t elements which
            # are not t-call ones)
            nb_real_elements_in_hierarchy = 0
            node = el
            while node is not None and nb_real_elements_in_hierarchy < 2:
                if node.tag != 't' or 't-call' in node.attrib:
                    nb_real_elements_in_hierarchy += 1
                node = node.getparent()
            if nb_real_elements_in_hierarchy == 1:
                # The first node might be a call to a sub template
                sub_call = el.get('t-call')
                if sub_call:
                    el.set('t-options', f"{{'snippet-key': '{snippet_key}', 'snippet-sub-call-key': '{sub_call}'}}")
                # If it already has a data-snippet it is a saved snippet.
                # Do not override it.
                elif 'data-snippet' not in el.attrib:
                    el.attrib['data-snippet'] = snippet_key.split('.', 1)[-1]

        return super()._compile_node(el, compile_context, indent)

    # compile directives

    def _compile_directive_snippet(self, el, compile_context, indent):
        key = el.attrib.pop('t-snippet')
        el.set('t-call', key)
        snippet_lang = self._context.get('snippet_lang')
        if snippet_lang:
            el.set('t-lang', f"'{snippet_lang}'")

        el.set('t-options', f"{{'snippet-key': {key!r}}}")
        view = self.env['ir.ui.view']._get(key).sudo()
        name = view.name
        thumbnail = el.attrib.pop('t-thumbnail', "oe-thumbnail")
        # Forbid sanitize contains the specific reason:
        # - "true": always forbid
        # - "form": forbid if forms are sanitized
        forbid_sanitize = el.attrib.pop('t-forbid-sanitize', None)
        div = '<div name="%s" data-oe-type="snippet" data-oe-thumbnail="%s" data-oe-snippet-id="%s" data-oe-keywords="%s" %s>' % (
            escape(pycompat.to_text(name)),
            escape(pycompat.to_text(thumbnail)),
            escape(pycompat.to_text(view.id)),
            escape(pycompat.to_text(el.findtext('keywords'))),
            f'data-oe-forbid-sanitize="{forbid_sanitize}"' if forbid_sanitize else '',
        )
        self._append_text(div, compile_context)
        code = self._compile_node(el, compile_context, indent)
        self._append_text('</div>', compile_context)
        return code

    def _compile_directive_snippet_call(self, el, compile_context, indent):
        key = el.attrib.pop('t-snippet-call')
        el.set('t-call', key)
        el.set('t-options', f"{{'snippet-key': {key!r}}}")
        return self._compile_node(el, compile_context, indent)

    def _compile_directive_install(self, el, compile_context, indent):
        key = el.attrib.pop('t-install')
        thumbnail = el.attrib.pop('t-thumbnail', 'oe-thumbnail')
        if self.user_has_groups('base.group_system'):
            module = self.env['ir.module.module'].search([('name', '=', key)])
            if not module or module.state == 'installed':
                return []
            name = el.attrib.get('string') or 'Snippet'
            div = '<div name="%s" data-oe-type="snippet" data-module-id="%s" data-oe-thumbnail="%s"><section/></div>' % (
                escape(pycompat.to_text(name)),
                module.id,
                escape(pycompat.to_text(thumbnail))
            )
            self._append_text(div, compile_context)
        return []

    def _compile_directive_placeholder(self, el, compile_context, indent):
        el.set('t-att-placeholder', el.attrib.pop('t-placeholder'))
        return []

    # order and ignore

    def _directives_eval_order(self):
        directives = super()._directives_eval_order()
        # Insert before "att" as those may rely on static attributes like
        # "string" and "att" clears all of those
        index = directives.index('att') - 1
        directives.insert(index, 'placeholder')
        directives.insert(index, 'snippet')
        directives.insert(index, 'snippet-call')
        directives.insert(index, 'install')
        return directives

    def _get_template_cache_keys(self):
        return super()._get_template_cache_keys() + ['snippet_lang']


#------------------------------------------------------
# QWeb fields
#------------------------------------------------------


class Field(models.AbstractModel):
    _name = 'ir.qweb.field'
    _description = 'Qweb Field'
    _inherit = 'ir.qweb.field'

    @api.model
    def attributes(self, record, field_name, options, values):
        attrs = super(Field, self).attributes(record, field_name, options, values)
        field = record._fields[field_name]

        placeholder = options.get('placeholder') or getattr(field, 'placeholder', None)
        if placeholder:
            attrs['placeholder'] = placeholder

        if options['translate'] and field.type in ('char', 'text'):
            lang = record.env.lang or 'en_US'
            if lang == 'en_US':
                attrs['data-oe-translation-state'] = 'translated'
            else:
                value_en = record.with_context(lang='en_US')[field_name]
                value_lang = record.with_context(lang=lang)[field_name]
                attrs['data-oe-translation-state'] = 'translated' if value_en != value_lang else 'to_translate'

        return attrs

    def value_from_string(self, value):
        return value

    @api.model
    def from_html(self, model, field, element):
        return self.value_from_string(element.text_content().strip())


class Integer(models.AbstractModel):
    _name = 'ir.qweb.field.integer'
    _description = 'Qweb Field Integer'
    _inherit = 'ir.qweb.field.integer'

    @api.model
    def from_html(self, model, field, element):
        lang = self.user_lang()
        value = element.text_content().strip()
        return int(value.replace(lang.thousands_sep, ''))


class Float(models.AbstractModel):
    _name = 'ir.qweb.field.float'
    _description = 'Qweb Field Float'
    _inherit = 'ir.qweb.field.float'

    @api.model
    def from_html(self, model, field, element):
        lang = self.user_lang()
        value = element.text_content().strip()
        return float(value.replace(lang.thousands_sep, '')
                          .replace(lang.decimal_point, '.'))


class ManyToOne(models.AbstractModel):
    _name = 'ir.qweb.field.many2one'
    _description = 'Qweb Field Many to One'
    _inherit = 'ir.qweb.field.many2one'

    @api.model
    def attributes(self, record, field_name, options, values):
        attrs = super(ManyToOne, self).attributes(record, field_name, options, values)
        if options.get('inherit_branding'):
            many2one = getattr(record, field_name)
            if many2one:
                attrs['data-oe-many2one-id'] = many2one.id
                attrs['data-oe-many2one-model'] = many2one._name
        return attrs

    @api.model
    def from_html(self, model, field, element):
        Model = self.env[element.get('data-oe-model')]
        id = int(element.get('data-oe-id'))
        M2O = self.env[field.comodel_name]
        field_name = element.get('data-oe-field')
        many2one_id = int(element.get('data-oe-many2one-id'))
        record = many2one_id and M2O.browse(many2one_id)
        if record and record.exists():
            # save the new id of the many2one
            Model.browse(id).write({field_name: many2one_id})

        # not necessary, but might as well be explicit about it
        return None


class Contact(models.AbstractModel):
    _name = 'ir.qweb.field.contact'
    _description = 'Qweb Field Contact'
    _inherit = 'ir.qweb.field.contact'

    @api.model
    def attributes(self, record, field_name, options, values):
        attrs = super(Contact, self).attributes(record, field_name, options, values)
        if options.get('inherit_branding'):
            attrs['data-oe-contact-options'] = json.dumps(options)
        return attrs

    # helper to call the rendering of contact field
    @api.model
    def get_record_to_html(self, ids, options=None):
        return self.value_to_html(self.env['res.partner'].search([('id', '=', ids[0])]), options=options)


class Date(models.AbstractModel):
    _name = 'ir.qweb.field.date'
    _description = 'Qweb Field Date'
    _inherit = 'ir.qweb.field.date'

    @api.model
    def attributes(self, record, field_name, options, values):
        attrs = super(Date, self).attributes(record, field_name, options, values)
        if options.get('inherit_branding'):
            attrs['data-oe-original'] = record[field_name]

            if record._fields[field_name].type == 'datetime':
                attrs = self.env['ir.qweb.field.datetime'].attributes(record, field_name, options, values)
                attrs['data-oe-type'] = 'datetime'
                return attrs

            lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
            locale = babel_locale_parse(lg.code)
            babel_format = value_format = posix_to_ldml(lg.date_format, locale=locale)

            if record[field_name]:
                date = fields.Date.from_string(record[field_name])
                value_format = pycompat.to_text(babel.dates.format_date(date, format=babel_format, locale=locale))

            attrs['data-oe-original-with-format'] = value_format
        return attrs

    @api.model
    def from_html(self, model, field, element):
        value = element.text_content().strip()
        if not value:
            return False

        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        date = datetime.strptime(value, lg.date_format)
        return fields.Date.to_string(date)


class DateTime(models.AbstractModel):
    _name = 'ir.qweb.field.datetime'
    _description = 'Qweb Field Datetime'
    _inherit = 'ir.qweb.field.datetime'

    @api.model
    def attributes(self, record, field_name, options, values):
        attrs = super(DateTime, self).attributes(record, field_name, options, values)

        if options.get('inherit_branding'):
            value = record[field_name]

            lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
            locale = babel_locale_parse(lg.code)
            babel_format = value_format = posix_to_ldml('%s %s' % (lg.date_format, lg.time_format), locale=locale)
            tz = record.env.context.get('tz') or self.env.user.tz

            if isinstance(value, str):
                value = fields.Datetime.from_string(value)

            if value:
                # convert from UTC (server timezone) to user timezone
                value = fields.Datetime.context_timestamp(self.with_context(tz=tz), timestamp=value)
                value_format = pycompat.to_text(babel.dates.format_datetime(value, format=babel_format, locale=locale))
                value = fields.Datetime.to_string(value)

            attrs['data-oe-original'] = value
            attrs['data-oe-original-with-format'] = value_format
            attrs['data-oe-original-tz'] = tz
        return attrs

    @api.model
    def from_html(self, model, field, element):
        value = element.text_content().strip()
        if not value:
            return False

        # parse from string to datetime
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        try:
            datetime_format = f'{lg.date_format} {lg.time_format}'
            dt = datetime.strptime(value, datetime_format)
        except ValueError:
            raise ValidationError(_("The datetime %s does not match the format %s", value, datetime_format))

        # convert back from user's timezone to UTC
        tz_name = element.attrib.get('data-oe-original-tz') or self.env.context.get('tz') or self.env.user.tz
        if tz_name:
            try:
                user_tz = pytz.timezone(tz_name)
                utc = pytz.utc

                dt = user_tz.localize(dt).astimezone(utc)
            except Exception:
                logger.warning(
                    "Failed to convert the value for a field of the model"
                    " %s back from the user's timezone (%s) to UTC",
                    model, tz_name,
                    exc_info=True)

        # format back to string
        return fields.Datetime.to_string(dt)


class Text(models.AbstractModel):
    _name = 'ir.qweb.field.text'
    _description = 'Qweb Field Text'
    _inherit = 'ir.qweb.field.text'

    @api.model
    def from_html(self, model, field, element):
        return html_to_text(element)


class Selection(models.AbstractModel):
    _name = 'ir.qweb.field.selection'
    _description = 'Qweb Field Selection'
    _inherit = 'ir.qweb.field.selection'

    @api.model
    def from_html(self, model, field, element):
        value = element.text_content().strip()
        selection = field.get_description(self.env)['selection']
        for k, v in selection:
            if isinstance(v, str):
                v = ustr(v)
            if value == v:
                return k

        raise ValueError(u"No value found for label %s in selection %s" % (
                         value, selection))


class HTML(models.AbstractModel):
    _name = 'ir.qweb.field.html'
    _description = 'Qweb Field HTML'
    _inherit = 'ir.qweb.field.html'

    @api.model
    def attributes(self, record, field_name, options, values=None):
        attrs = super().attributes(record, field_name, options, values)
        if options.get('inherit_branding'):
            field = record._fields[field_name]
            if field.sanitize:
                if field.sanitize_overridable and not record.user_has_groups('base.group_sanitize_override'):
                    try:
                        field.convert_to_column(record[field_name], record)
                    except UserError:
                        # The field contains element(s) that would be removed if
                        # sanitized. It means that someone who was part of a
                        # group allowing to bypass the sanitation saved that
                        # field previously. Mark the field as not editable.
                        attrs['data-oe-sanitize-prevent-edition'] = 1
                if not (field.sanitize_overridable and record.user_has_groups('base.group_sanitize_override')):
                    # Don't mark the field as 'sanitize' if the sanitize is
                    # defined as overridable and the user has the right to do so
                    attrs['data-oe-sanitize'] = 1 if field.sanitize_form else 'allow_form'

        return attrs

    @api.model
    def from_html(self, model, field, element):
        content = []
        if element.text:
            content.append(element.text)
        content.extend(html.tostring(child, encoding='unicode')
                       for child in element.iterchildren(tag=etree.Element))
        return '\n'.join(content)


class Image(models.AbstractModel):
    """
    Widget options:

    ``class``
        set as attribute on the generated <img> tag
    """
    _name = 'ir.qweb.field.image'
    _description = 'Qweb Field Image'
    _inherit = 'ir.qweb.field.image'

    local_url_re = re.compile(r'^/(?P<module>[^]]+)/static/(?P<rest>.+)$')

    @api.model
    def from_html(self, model, field, element):
        if element.find('img') is None:
            return False
        url = element.find('img').get('src')

        url_object = urls.url_parse(url)
        if url_object.path.startswith('/web/image'):
            fragments = url_object.path.split('/')
            query = url_object.decode_query()
            url_id = fragments[3].split('-')[0]
            # ir.attachment image urls: /web/image/<id>[-<checksum>][/...]
            if url_id.isdigit():
                model = 'ir.attachment'
                oid = url_id
                field = 'datas'
            # url of binary field on model: /web/image/<model>/<id>/<field>[/...]
            else:
                model = query.get('model', fragments[3])
                oid = query.get('id', fragments[4])
                field = query.get('field', fragments[5])
            item = self.env[model].browse(int(oid))
            return item[field]

        if self.local_url_re.match(url_object.path):
            return self.load_local_url(url)

        return self.load_remote_url(url)

    def load_local_url(self, url):
        match = self.local_url_re.match(urls.url_parse(url).path)

        rest = match.group('rest')
        for sep in os.sep, os.altsep:
            if sep and sep != '/':
                rest.replace(sep, '/')

        path = odoo.modules.get_module_resource(
            match.group('module'), 'static', *(rest.split('/')))

        if not path:
            return None

        try:
            with open(path, 'rb') as f:
                # force complete image load to ensure it's valid image data
                image = I.open(f)
                image.load()
                f.seek(0)
                return base64.b64encode(f.read())
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

            req = requests.get(url, timeout=REMOTE_CONNECTION_TIMEOUT)
            # PIL needs a seekable file-like image so wrap result in IO buffer
            image = I.open(io.BytesIO(req.content))
            # force a complete load of the image data to validate it
            image.load()
        except Exception:
            logger.exception("Failed to load remote image %r", url)
            return None

        # don't use original data in case weird stuff was smuggled in, with
        # luck PIL will remove some of it?
        out = io.BytesIO()
        image.save(out, image.format)
        return base64.b64encode(out.getvalue())


class Monetary(models.AbstractModel):
    _name = 'ir.qweb.field.monetary'
    _inherit = 'ir.qweb.field.monetary'

    @api.model
    def from_html(self, model, field, element):
        lang = self.user_lang()

        value = element.find('span').text.strip()

        return float(value.replace(lang.thousands_sep, '')
                          .replace(lang.decimal_point, '.'))


class Duration(models.AbstractModel):
    _name = 'ir.qweb.field.duration'
    _description = 'Qweb Field Duration'
    _inherit = 'ir.qweb.field.duration'

    @api.model
    def attributes(self, record, field_name, options, values):
        attrs = super(Duration, self).attributes(record, field_name, options, values)
        if options.get('inherit_branding'):
            attrs['data-oe-original'] = record[field_name]
        return attrs

    @api.model
    def from_html(self, model, field, element):
        value = element.text_content().strip()

        # non-localized value
        return float(value)


class RelativeDatetime(models.AbstractModel):
    _name = 'ir.qweb.field.relative'
    _description = 'Qweb Field Relative'
    _inherit = 'ir.qweb.field.relative'

    # get formatting from ir.qweb.field.relative but edition/save from datetime


class QwebView(models.AbstractModel):
    _name = 'ir.qweb.field.qweb'
    _description = 'Qweb Field qweb'
    _inherit = 'ir.qweb.field.qweb'


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
    padding = 0
    for item in it:
        if isinstance(item, int):
            padding = max(padding, item)
            continue

        if padding:
            yield '\n' * padding
            padding = 0

        yield item
    # leftover padding irrelevant as the output will be stripped


def _wrap(element, output, wrapper=''):
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
        output.append('\n')
    elif e.tag in _PADDED_BLOCK:
        _wrap(e, output, 2)
    elif e.tag in _MISC_BLOCK:
        _wrap(e, output, 1)
    else:
        # inline
        _wrap(e, output)

    if e.tail:
        output.append(_collapse_whitespace(e.tail))
