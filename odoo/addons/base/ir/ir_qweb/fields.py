# -*- coding: utf-8 -*-
import re
from collections import OrderedDict
from odoo import api, fields, models, _
from PIL import Image
from cStringIO import StringIO
import babel
from odoo.tools import html_escape as escape, posix_to_ldml, safe_eval, float_utils, format_date
from .qweb import unicodifier

import logging
_logger = logging.getLogger(__name__)


def nl2br(string):
    """ Converts newlines to HTML linebreaks in ``string``. returns
    the unicode result

    :param str string:
    :rtype: unicode
    """
    return unicodifier(string).replace(u'\n', u'<br>\n')

def html_escape(string, options):
    """ Automatically escapes content unless options['html-escape']
    is set to False

    :param str string:
    :param dict options:
    """
    return escape(string) if not options or options.get('html-escape', True) else string

#--------------------------------------------------------------------
# QWeb Fields converters
#--------------------------------------------------------------------

class FieldConverter(models.AbstractModel):
    """ Used to convert a t-field specification into an output HTML field.

    :meth:`~.to_html` is the entry point of this conversion from QWeb, it:

    * converts the record value to html using :meth:`~.record_to_html`
    * generates the metadata attributes (``data-oe-``) to set on the root
      result node
    * generates the root result node itself through :meth:`~.render_element`
    """
    _name = 'ir.qweb.field'

    @api.model
    def attributes(self, record, field_name, options, values=None):
        """ attributes(record, field_name, field, options, values)

        Generates the metadata attributes (prefixed by ``data-oe-``) for the
        root node of the field conversion.

        The default attributes are:

        * ``model``, the name of the record's model
        * ``id`` the id of the record to which the field belongs
        * ``type`` the logical field type (widget, may not match the field's
          ``type``, may not be any Field subclass name)
        * ``translate``, a boolean flag (``0`` or ``1``) denoting whether the
          field is translatable
        * ``readonly``, has this attribute if the field is readonly
        * ``expression``, the original expression

        :returns: OrderedDict (attribute name, attribute value).
        """
        data = OrderedDict()
        field = record._fields[field_name]

        if not options['inherit_branding'] and not options['translate']:
            return data

        data['data-oe-model'] = record._name
        data['data-oe-id'] = record.id
        data['data-oe-field'] = field.name
        data['data-oe-type'] = options.get('type')
        data['data-oe-expression'] = options.get('expression')
        if field.readonly:
            data['data-oe-readonly'] = 1
        return data

    @api.model
    def value_to_html(self, value, options):
        """ value_to_html(value, field, options=None)

        Converts a single value to its HTML version/output
        :rtype: unicode
        """
        return html_escape(unicodifier(value) or u'', options)

    @api.model
    def record_to_html(self, record, field_name, options):
        """ record_to_html(record, field_name, options)

        Converts the specified field of the browse_record ``record`` to HTML
        :rtype: unicode
        """
        if not record:
            return False
        value = record[field_name]
        return False if value is False else record.env[self._name].value_to_html(value, options=options)

    @api.model
    def user_lang(self):
        """ user_lang()

        Fetches the res.lang record corresponding to the language code stored
        in the user's context. Fallbacks to en_US if no lang is present in the
        context *or the language code is not valid*.

        :returns: res.lang browse_record
        """
        lang_code = self._context.get('lang') or 'en_US'
        return self.env['res.lang']._lang_get(lang_code)


class IntegerConverter(models.AbstractModel):
    _name = 'ir.qweb.field.integer'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        return unicodifier(self.user_lang().format('%d', value, grouping=True).replace(r'-', u'\u2011'))


class FloatConverter(models.AbstractModel):
    _name = 'ir.qweb.field.float'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        if 'decimal_precision' in options:
            precision = self.env['decimal.precision'].search([('name', '=', options['decimal_precision'])]).digits
        else:
            precision = options['precision']

        if precision is None:
            fmt = '%f'
        else:
            value = float_utils.float_round(value, precision_digits=precision)
            fmt = '%.{precision}f'.format(precision=precision)

        formatted = self.user_lang().format(fmt, value, grouping=True).replace(r'-', u'\u2011')

        # %f does not strip trailing zeroes. %g does but its precision causes
        # it to switch to scientific notation starting at a million *and* to
        # strip decimals. So use %f and if no precision was specified manually
        # strip trailing 0.
        if precision is None:
            formatted = re.sub(r'(?:(0|\d+?)0+)$', r'\1', formatted)

        return unicodifier(formatted)

    @api.model
    def record_to_html(self, record, field_name, options):
        if 'precision' not in options and 'decimal_precision' not in options:
            _, precision = record._fields[field_name].digits or (None, None)
            options = dict(options, precision=precision)
        return super(FloatConverter, self).record_to_html(record, field_name, options)


class DateConverter(models.AbstractModel):
    _name = 'ir.qweb.field.date'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        return format_date(self.env, value, date_format=(options or {}).get('format'))


class DateTimeConverter(models.AbstractModel):
    _name = 'ir.qweb.field.datetime'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        if not value:
            return ''
        lang = self.user_lang()
        locale = babel.Locale.parse(lang.code)

        if isinstance(value, basestring):
            value = fields.Datetime.from_string(value)

        value = fields.Datetime.context_timestamp(self, value)

        if options and 'format' in options:
            pattern = options['format']
        else:
            if options and options.get('time_only'):
                strftime_pattern = (u"%s" % (lang.time_format))
            else:
                strftime_pattern = (u"%s %s" % (lang.date_format, lang.time_format))

            pattern = posix_to_ldml(strftime_pattern, locale=locale)

        if options and options.get('hide_seconds'):
            pattern = pattern.replace(":ss", "").replace(":s", "")

        return unicodifier(babel.dates.format_datetime(value, format=pattern, locale=locale))


class TextConverter(models.AbstractModel):
    _name = 'ir.qweb.field.text'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        """
        Escapes the value and converts newlines to br. This is bullshit.
        """
        return nl2br(html_escape(value, options)) if value else ''


class SelectionConverter(models.AbstractModel):
    _name = 'ir.qweb.field.selection'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        if not value:
            return ''
        return html_escape(unicodifier(options['selection'][value]) or u'', options)

    @api.model
    def record_to_html(self, record, field_name, options):
        if 'selection' not in options:
            options = dict(options, selection=dict(record._fields[field_name].get_description(self.env)['selection']))
        return super(SelectionConverter, self).record_to_html(record, field_name, options)


class ManyToOneConverter(models.AbstractModel):
    _name = 'ir.qweb.field.many2one'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        if not value:
            return False
        value = value.sudo().display_name
        if not value:
            return False
        return nl2br(html_escape(value, options)) if value else ''


class HTMLConverter(models.AbstractModel):
    _name = 'ir.qweb.field.html'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        return unicodifier(value) or u''


class ImageConverter(models.AbstractModel):
    """ ``image`` widget rendering, inserts a data:uri-using image tag in the
    document. May be overridden by e.g. the website module to generate links
    instead.

    .. todo:: what happens if different output need different converters? e.g.
              reports may need embedded images or FS links whereas website
              needs website-aware
    """
    _name = 'ir.qweb.field.image'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        try:
            image = Image.open(StringIO(value.decode('base64')))
            image.verify()
        except IOError:
            raise ValueError("Non-image binary fields can not be converted to HTML")
        except: # image.verify() throws "suitable exceptions", I have no idea what they are
            raise ValueError("Invalid image content")

        return unicodifier('<img src="data:%s;base64,%s">' % (Image.MIME[image.format], value))


class MonetaryConverter(models.AbstractModel):
    """ ``monetary`` converter, has a mandatory option
    ``display_currency`` only if field is not of type Monetary.
    Otherwise, if we are in presence of a monetary field, the field definition must
    have a currency_field attribute set.

    The currency is used for formatting *and rounding* of the float value. It
    is assumed that the linked res_currency has a non-empty rounding value and
    res.currency's ``round`` method is used to perform rounding.

    .. note:: the monetary converter internally adds the qweb context to its
              options mapping, so that the context is available to callees.
              It's set under the ``_values`` key.
    """
    _name = 'ir.qweb.field.monetary'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        display_currency = options['display_currency']

        # lang.format mandates a sprintf-style format. These formats are non-
        # minimal (they have a default fixed precision instead), and
        # lang.format will not set one by default. currency.round will not
        # provide one either. So we need to generate a precision value
        # (integer > 0) from the currency's rounding (a float generally < 1.0).
        fmt = "%.{0}f".format(display_currency.decimal_places)

        if options.get('from_currency'):
            value = options['from_currency'].compute(value, display_currency)

        lang = self.user_lang()
        formatted_amount = lang.format(fmt, display_currency.round(value),
                                grouping=True, monetary=True).replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'\u2011')

        pre = post = u''
        if display_currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=display_currency.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=display_currency.symbol or '')

        return u'{pre}<span class="oe_currency_value">{0}</span>{post}'.format(formatted_amount, pre=pre, post=post)

    @api.model
    def record_to_html(self, record, field_name, options):
        options = dict(options)
        #currency should be specified by monetary field
        field = record._fields[field_name]
        if not options.get('display_currency') and field.type == 'monetary' and field.currency_field:
            options['display_currency'] = record[field.currency_field]

        return super(MonetaryConverter, self).record_to_html(record, field_name, options)

TIMEDELTA_UNITS = (
    ('year',   3600 * 24 * 365),
    ('month',  3600 * 24 * 30),
    ('week',   3600 * 24 * 7),
    ('day',    3600 * 24),
    ('hour',   3600),
    ('minute', 60),
    ('second', 1)
)


class DurationConverter(models.AbstractModel):
    """ ``duration`` converter, to display integral or fractional values as
    human-readable time spans (e.g. 1.5 as "1 hour 30 minutes").

    Can be used on any numerical field.

    Has a mandatory option ``unit`` which can be one of ``second``, ``minute``,
    ``hour``, ``day``, ``week`` or ``year``, used to interpret the numerical
    field value before converting it.

    Sub-second values will be ignored.
    """
    _name = 'ir.qweb.field.duration'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        units = dict(TIMEDELTA_UNITS)

        if value < 0:
            raise ValueError(_("Durations can't be negative"))

        if not options or options.get('unit') not in units:
            raise ValueError(_("A unit must be provided to duration widgets"))

        locale = babel.Locale.parse(self.user_lang().code)
        factor = units[options['unit']]

        sections = []

        r = value * factor
        if options.get('round') in units:
            round_to = units[options['round']]
            r = round(r / round_to) * round_to

        for unit, secs_per_unit in TIMEDELTA_UNITS:
            v, r = divmod(r, secs_per_unit)
            if not v:
                continue
            section = babel.dates.format_timedelta(
                v*secs_per_unit, threshold=1, locale=locale)
            if section:
                sections.append(section)
        return u' '.join(sections)


class RelativeDatetimeConverter(models.AbstractModel):
    _name = 'ir.qweb.field.relative'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        locale = babel.Locale.parse(self.user_lang().code)

        if isinstance(value, basestring):
            value = fields.Datetime.from_string(value)

        # value should be a naive datetime in UTC. So is fields.Datetime.now()
        reference = fields.Datetime.from_string(options['now'])

        return unicodifier(babel.dates.format_timedelta(value - reference, add_direction=True, locale=locale))

    @api.model
    def record_to_html(self, record, field_name, options):
        if 'now' not in options:
            options = dict(options, now=record._fields[field_name].now())
        return super(RelativeDatetimeConverter, self).record_to_html(record, field_name, options)


class Contact(models.AbstractModel):
    _name = 'ir.qweb.field.contact'
    _inherit = 'ir.qweb.field.many2one'

    @api.model
    def value_to_html(self, value, options):
        if not value.exists():
            return False

        opf = options and options.get('fields') or ["name", "address", "phone", "mobile", "fax", "email"]
        value = value.sudo().with_context(show_address=True)
        name_get = value.name_get()[0][1]

        val = {
            'name': name_get.split("\n")[0],
            'address': escape("\n".join(name_get.split("\n")[1:])).strip(),
            'phone': value.phone,
            'mobile': value.mobile,
            'fax': value.fax,
            'city': value.city,
            'country_id': value.country_id.display_name,
            'website': value.website,
            'email': value.email,
            'fields': opf,
            'object': value,
            'options': options
        }
        return self.env['ir.qweb'].render('base.contact', val)


class QwebView(models.AbstractModel):
    _name = 'ir.qweb.field.qweb'
    _inherit = 'ir.qweb.field.many2one'

    @api.model
    def record_to_html(self, record, field_name, options):
        if not getattr(record, field_name):
            return None

        view = getattr(record, field_name)

        if view._name != "ir.ui.view":
            _logger.warning("%s.%s must be a 'ir.ui.view' model." % (record, field_name))
            return None

        view = view.with_context(object=record)

        return unicodifier(view.render(view._context, engine='ir.qweb'))
