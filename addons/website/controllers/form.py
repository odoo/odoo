# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import contextlib
import io
import json
import math
import operator
from collections import defaultdict
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from psycopg2 import IntegrityError
import re
from werkzeug.exceptions import BadRequest

from odoo import http, SUPERUSER_ID
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, BinaryBytes, plaintext2html
from odoo.exceptions import AccessDenied, ValidationError, UserError
from odoo.tools.misc import verify_hash_signed
from odoo.tools.translate import _, LazyTranslate

_lt = LazyTranslate(__name__)

# The values the browsers accept in the inputs of these types, loosely
INPUT_TYPE_RES = {
    'email': re.compile(r'[^\s@,]+@[^\s@,]+(,[^\s@,]+@[^\s@,]+)*'),  # several with the `multiple` attribute
    'url': re.compile(r'[a-zA-Z][a-zA-Z\d+.-]*:.*'),
    'number': re.compile(r'[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?'),
}


class WebsiteForm(http.Controller):

    @http.route('/website/form', type='http', auth="public", methods=['POST'], multilang=False, replica=True)
    def website_form_empty(self, **kwargs):
        # This is a workaround to don't add language prefix to <form action="/website/form/" ...>
        return ""

    # Check and insert values from the form on the model <model>
    @http.route('/website/form/<string:model_name>', type='http', auth="public", methods=['POST'], website=True, csrf=False, captcha='website_form')
    def website_form(self, model_name, **kwargs):
        # Partial CSRF check, only performed when session is authenticated, as there
        # is no real risk for unauthenticated sessions here. It's a common case for
        # embedded forms now: SameSite policy rejects the cookies, so the session
        # is lost, and the CSRF check fails, breaking the post for no good reason.
        csrf_token = request.params.pop('csrf_token', None)
        if request.session.uid and not request.validate_csrf(csrf_token):
            raise BadRequest('Session expired (invalid CSRF token)')

        try:
            # Verify the params in place, as some overrides read them, then
            # update kwargs to reflect the changes.
            request.params.pop('model_name')
            self._verify_website_form(model_name, request.params)
            kwargs = dict(request.params)
            res = self._handle_website_form(model_name, **kwargs)
            # try to save here
            self.env.cr.commit()
            return res
        except (ValidationError, UserError) as e:
            self.env.cr.rollback()
            return json.dumps({
                'error': e.args[0],
            })

    def _handle_website_form(self, model_name, **kwargs):
        model_record = request.env['ir.model'].sudo().search([('model', '=', model_name), ('website_form_access', '=', True)])
        if not model_record:
            return json.dumps({
                'error': _("This form cannot be submitted. Please contact the website administrator."),
            })

        try:
            data = self.extract_data(model_record, kwargs)
        # If we encounter an issue while extracting data
        except ValidationError as e:
            # I couldn't find a cleaner way to pass data to an exception
            return json.dumps({'error_fields': e.args[0]})

        try:
            id_record = self.insert_record(request, model_record, data['record'], data['custom'], data.get('meta'))
            if id_record:
                self.insert_attachment(model_record, id_record, data['attachments'])
                # in case of an email, we want to send it immediately instead of waiting
                # for the email queue to process

                if model_name == 'mail.mail':
                    request.env[model_name].sudo().browse(id_record).send()

        # Some fields have additional SQL constraints that we can't check generically
        # Ex: crm.lead.probability which is a float between 0 and 1
        # TODO: How to get the name of the erroneous field ?
        except IntegrityError:
            return json.dumps(False)

        request.session['form_builder_model_model'] = model_record.model
        request.session['form_builder_model'] = model_record.name
        request.session['form_builder_id'] = id_record

        return json.dumps({'id': id_record})

    def _verify_website_form(self, model_name, values):
        """ Check the submitted values against the form, signed when it was
        rendered (see `sign_website_forms`), so that it cannot be forged: only
        its inputs can be submitted, with values passing the checks of form.js
        (options, required, length, type, requirement rule, files), the hidden
        inputs keep their value, and the inputs of the fields hidden by their
        visibility rule are not submitted, as form.js disables them.

        :param str model_name: the model targeted by the submission
        :param dict values: the submitted values, updated in place
        """
        try:
            form = verify_hash_signed(request.env(su=True), 'website_form_signature', values.pop('website_form_signature', ''))
        except (AttributeError, ValueError):  # malformed signature
            form = None
        if not form or form['model'] != model_name:
            raise AccessDenied(_("This form has been modified. Please reload the page and try again."))

        inputs = form['inputs']
        keys = defaultdict(list)  # the submitted keys of each input
        for key, value in values.items():
            # Undo file upload field name indexing, e.g. `CV [PDF][0][1]` (see `send` in form.js)
            is_file = hasattr(value, 'filename')
            name = key.rsplit('[', 2)[0] if is_file else key
            if name not in inputs or is_file != (inputs[name].get('type') == 'file'):
                raise AccessDenied(_('The "%s" field has been modified. Please reload the page and try again.', name))
            keys[name].append(key)
        for name, rules in inputs.items():
            if 'value' in rules:  # the visitor cannot change it
                for key in keys.pop(name, []):
                    del values[key]
                value = self._format_website_form_date(rules) if 'date' in rules else rules['value']
                if value:
                    values[name] = value
                    keys[name].append(name)

        submitted = {
            name: self._get_website_form_values(rules, [values[key] for key in keys[name]])
            for name, rules in inputs.items()
        }
        for name, rules in inputs.items():
            if not self._is_website_form_input_visible(inputs, submitted, name):
                for key in keys[name]:
                    del values[key]
            elif 'value' not in rules and not self._check_website_form_values(rules, submitted[name]):
                raise AccessDenied(_('The "%s" field has been modified. Please reload the page and try again.', name))

    def _get_website_form_values(self, rules, values):
        """ Return the values submitted for an input, like `FormData.getAll`,
        or None if they are not options of the input. The options of a multiple
        choice are submitted together, separated by commas (see `send` in
        form.js), while they can contain commas too.
        """
        values = [value for value in values if value]  # form.js does not submit the empty values
        options = rules.get('options')
        if values and rules.get('multiple') and rules.get('type') != 'file':
            options_by_length = sorted(options or [], key=len, reverse=True)
            remaining, values = values[0], []
            while remaining:
                value = next(
                    (option for option in options_by_length if f'{remaining},'.startswith(f'{option},')),
                    remaining.split(',', 1)[0],
                )
                values.append(value)
                remaining = remaining[len(value) + 1:]
        return values if options is None or set(values) <= set(options) else None

    def _check_website_form_values(self, rules, values):
        """ Return whether the values submitted for an input (see
        `_get_website_form_values`) pass the checks of form.js before
        submitting them (see `checkErrorFields`).
        """
        if not values:
            return values is not None and not rules.get('required')
        if rules.get('type') == 'file':
            # See `isFileInputValid` in form.js
            accept = {mimetype.strip() for mimetype in rules.get('accept', '').split(',')} - {''}
            for file in values:
                size = file.stream.seek(0, io.SEEK_END)
                file.stream.seek(0)
                if size > rules.get('data-max-file-size', math.inf) * 1_000_000:
                    return False
                # The browsers submit the files of unknown type as `application/octet-stream`.
                mimetypes = {file.mimetype, f"{file.mimetype.split('/')[0]}/*"}
                if accept and file.mimetype not in ('', 'application/octet-stream') and not mimetypes & accept:
                    return False
            return len(values) <= rules.get('data-max-files-number', math.inf if rules.get('multiple') else 1)

        value = ','.join(values)
        # JS counts the UTF-16 code units, and the new lines of the textareas as
        # one character, while the browsers submit them as CRLF.
        length = len(value.replace('\r\n', '\n').encode('utf-16-le')) // 2
        if not rules.get('minlength', 0) <= length <= rules.get('maxlength', math.inf):
            return False
        if rules.get('type') in INPUT_TYPE_RES and not INPUT_TYPE_RES[rules['type']].fullmatch(value):
            return False
        if rules.get('type') == 'number' and rules.get('step'):
            steps = float(value) / rules['step']  # e.g. a whole number for the integer fields
            if not math.isfinite(steps) or not math.isclose(steps, round(steps), abs_tol=1e-9):
                return False
        # See `requirementFunction` in form.js
        comparator, condition, between = rules.get('requirement', [None, None, None])
        if not condition or not value.strip() or (comparator in ('between', '!between') and not between):
            return True
        if rules.get('type') == 'email' and comparator in ('substring', '!substring'):
            value = value.split('@')[0]
        return self._compare_website_form_value(comparator, [value], condition, between, rules.get('server-format'))

    def _is_website_form_input_visible(self, inputs, submitted, name):
        # See `buildVisibilityFunction` in form.js
        return not inputs.get(name, {}).get('visibility') or any(
            self._is_website_form_input_visible(inputs, submitted, dependency)
            and self._compare_website_form_value(
                comparator, submitted.get(dependency) or [], condition, between, inputs.get(dependency, {}).get('server-format'),
            )
            for dependency, comparator, condition, between in inputs[name]['visibility']
        )

    def _compare_website_form_value(self, comparator, values, condition, between, server_format):
        """ Compare the values submitted for an input (see
        `_get_website_form_values`) like `compareTo` in form.js, to evaluate
        the visibility and requirement rules of the fields. The unknown
        comparisons pass.
        """
        value = values[0] if values else ''  # like `FormData.get`
        match comparator.removeprefix('!'):
            case 'contains':
                try:
                    parsed_condition = json.loads(condition)  # e.g. the options of a multiple choice
                except ValueError:
                    parsed_condition = condition
                if isinstance(parsed_condition, list):
                    result = any(item in values for item in parsed_condition)
                else:
                    result = (parsed_condition if isinstance(parsed_condition, str) else condition) in ','.join(values)
            case 'substring' | 'domain':
                words = [item['requirement_text'].strip().lower() for item in json.loads(condition)]
                if not words:
                    return True
                if comparator == 'domain':
                    result = any(value.lower().endswith(f'@{word}') for word in words)
                else:
                    result = any(word in value.strip().lower() for word in words)
            case 'equal' | 'selected':
                result = value == condition
            case 'set' | 'fileSet':
                result = bool(values)
            case 'greater' | 'less' | 'greater or equal' | 'less or equal':
                compare = {'greater': operator.gt, 'less': operator.lt, 'greater or equal': operator.ge, 'less or equal': operator.le}
                result = compare[comparator](self._parse_website_form_number(value), self._parse_website_form_number(condition))
            case 'dateEqual' | 'date!equal' | 'before' | 'after' | 'equal or before' | 'equal or after' | 'between' | 'lessyears':
                return self._compare_website_form_dates(comparator, value, condition, between, server_format)
            case _:
                return True
        return result != comparator.startswith('!')

    def _get_website_form_date_format(self, is_datetime, server_format):
        """ Return the format and the timezone of the dates submitted by form.js,
        i.e. as displayed in the timezone of the visitor, except for the model
        fields, in the server format, and in UTC for the datetimes (see `send`
        and `web.frontend_layout`).
        """
        tz = UTC
        with contextlib.suppress(KeyError, ValueError):
            tz = ZoneInfo(request.cookies.get('tz', 'UTC'))
        if server_format:
            return (DEFAULT_SERVER_DATETIME_FORMAT, UTC) if is_datetime else (DEFAULT_SERVER_DATE_FORMAT, tz)
        lang = request.lang
        return (f'{lang.date_format} {lang.time_format}' if is_datetime else lang.date_format), tz

    def _format_website_form_date(self, rules):
        """ Return the default value of a hidden date input, a timestamp, as
        submitted once displayed by its date picker (see `prepareDateFields` in
        form.js).
        """
        timestamp = self._parse_website_form_number(rules['value'])
        if math.isnan(timestamp):
            return ''
        date_format, tz = self._get_website_form_date_format(rules['date'] == 'datetime', rules.get('server-format'))
        return datetime.fromtimestamp(int(timestamp), tz).strftime(date_format)

    def _compare_website_form_dates(self, comparator, value, condition, between, server_format):
        """ Compare a submitted date like `compareTo` in form.js, i.e. as a
        timestamp in the timezone of the visitor.
        """
        is_datetime = ':' in value
        date_format, tz = self._get_website_form_date_format(is_datetime, server_format)
        try:
            date = datetime.strptime(value, date_format).replace(tzinfo=tz)
        except ValueError:  # e.g. a translated meridiem, while the date fields refuse the invalid dates
            return True

        now = datetime.now(tz)
        today = now.replace(second=0, microsecond=0) if is_datetime else now.replace(hour=0, minute=0, second=0, microsecond=0)
        if comparator == 'lessyears':
            years = self._parse_website_form_number(condition)
            return not math.isnan(years) and date > today - relativedelta(years=int(years))
        timestamp = date.timestamp()
        start = today.timestamp() if condition == 'today' else self._parse_website_form_number(condition)
        end = self._parse_website_form_number(between)
        match comparator:
            case 'dateEqual':
                return timestamp == start
            case 'date!equal':
                return timestamp != start
            case 'before':
                return timestamp < start
            case 'after':
                return timestamp > start
            case 'equal or before':
                return timestamp <= start
            case 'equal or after':
                return timestamp >= start
            case 'between':
                return start <= timestamp <= end
            case '!between':
                return not start <= timestamp <= end

    def _parse_website_form_number(self, value):
        # Like `parseFloat` in JS
        match = re.match(r'\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?', value or '')
        return float(match[0]) if match else math.nan

    # Constants string to make metadata readable on a text field

    _meta_label = _lt("Metadata")  # Title for meta data

    # Dict of dynamically called filters following type of field to be fault tolerent

    def identity(self, field_label, field_input):
        return field_input

    def integer(self, field_label, field_input):
        return int(field_input)

    def floating(self, field_label, field_input):
        return float(field_input)

    def html(self, field_label, field_input):
        return plaintext2html(field_input)

    def boolean(self, field_label, field_input):
        return bool(field_input)

    def binary(self, field_label, field_input):
        return base64.b64encode(field_input.read())

    def one2many(self, field_label, field_input):
        return [int(i) for i in field_input.split(',')]

    def many2many(self, field_label, field_input, *args):
        return [(args[0] if args else (6, 0)) + (self.one2many(field_label, field_input),)]

    def tags(self, field_label, field_input):
        # Unescape ',' and '\'
        return [
            tag.replace('\\,', ',').replace('\\/', '\\')
            for tag in re.split(r'(?<!\\),', field_input)
        ]

    _input_filters = {
        'char': identity,
        'text': identity,
        'html': html,
        'date': identity,
        'datetime': identity,
        'many2one': integer,
        'one2many': one2many,
        'many2many': many2many,
        'selection': identity,
        'boolean': boolean,
        'integer': integer,
        'float': floating,
        'binary': binary,
        'monetary': floating,
        # Properties
        'tags': tags,
    }

    # Extract all data sent by the form and sort its on several properties
    def extract_data(self, model_sudo, values):
        if not model_sudo.env.su:
            raise ValueError("model_sudo should get passed with sudo")
        dest_model = request.env[model_sudo.model]

        data = {
            'record': {},        # Values to create record
            'attachments': [],  # Attached files
            'custom': '',        # Custom fields values
            'meta': '',         # Add metadata if enabled
        }

        authorized_fields = model_sudo.with_user(SUPERUSER_ID)._get_form_writable_fields(values)
        error_fields = []
        custom_fields = []

        for field_name, field_value in values.items():
            # First decode the field_name encoded at the client side.
            field_name = re.sub('&quot;', '"', field_name)

            # If the value of the field if a file
            if hasattr(field_value, 'filename'):
                # Undo file upload field name indexing
                field_name = field_name.split('[', 1)[0]

                # If it's an actual binary field, convert the input file
                # If it's not, we'll use attachments instead
                if field_name in authorized_fields and authorized_fields[field_name]['type'] == 'binary':
                    data['record'][field_name] = BinaryBytes(field_value.read())
                    field_value.stream.seek(0)  # do not consume value forever
                    if field_name + "_filename" in dest_model:
                        data['record'][field_name + "_filename"] = field_value.filename
                else:
                    field_value.field_name = field_name
                    data['attachments'].append(field_value)

            # If it's a known field
            elif field_name in authorized_fields:
                try:
                    if '_property' in authorized_fields[field_name]:
                        # Collect all properties for a given property field in
                        # a list.
                        field_data = authorized_fields[field_name]
                        properties_field_name = field_data['_property']['field']
                        del field_data['_property']
                        properties = data['record'].setdefault(properties_field_name, [])
                        property_type = authorized_fields[field_name]['type']
                        # For properties, many2many is stored as an array of
                        # integers like one2many
                        filter_type = 'one2many' if property_type == 'many2many' else property_type
                        input_filter = self._input_filters[filter_type]
                        field_data['value'] = input_filter(self, field_name, field_value)
                        properties.append(field_data)
                    else:
                        input_filter = self._input_filters[authorized_fields[field_name]['type']]
                        data['record'][field_name] = input_filter(self, field_name, field_value)
                except ValueError:
                    error_fields.append(field_name)

                if dest_model._name == 'mail.mail' and field_name == 'email_from':
                    # As the "email_from" is used to populate the email_from of the
                    # sent mail.mail, it could be filtered out at sending time if no
                    # outgoing mail server "from_filter" match the sender email.
                    # To make sure the email contains that (important) information
                    # we also add it to the "custom message" that will be included
                    # in the body of the email sent.
                    custom_fields.append((_('email'), field_value))

            # If it's a custom field
            elif field_name not in ('context', 'website_form_signature'):
                custom_fields.append((field_name, field_value))

        data['custom'] = "\n".join([u"%s : %s" % v for v in custom_fields])

        # Add metadata if enabled  # ICP for retrocompatibility
        if request.env['ir.config_parameter'].sudo().get_bool('website_form_enable_metadata'):
            environ = request.httprequest.headers.environ
            data['meta'] += "%s : %s\n%s : %s\n%s : %s\n%s : %s\n" % (
                "IP", environ.get("REMOTE_ADDR"),
                "USER_AGENT", environ.get("HTTP_USER_AGENT"),
                "ACCEPT_LANGUAGE", environ.get("HTTP_ACCEPT_LANGUAGE"),
                "REFERER", environ.get("HTTP_REFERER")
            )

        # This function can be defined on any model to provide
        # a model-specific filtering of the record values
        # Example:
        # def website_form_input_filter(self, values):
        #     values['name'] = '%s\'s Application' % values['partner_name']
        #     return values
        if hasattr(dest_model, "website_form_input_filter"):
            data['record'] = dest_model.website_form_input_filter(request, data['record'])

        missing_required_fields = [label for label, field in authorized_fields.items() if field['required'] and label not in data['record']]
        if any(error_fields):
            raise ValidationError(error_fields + missing_required_fields)

        return data

    def insert_record(self, request, model_sudo, values, custom, meta=None):
        if not model_sudo.env.su:
            raise ValueError("model_sudo should get passed with sudo")
        model_name = model_sudo.model
        if model_name == 'mail.mail':
            email_from = _('"%(company)s form submission" <%(email)s>', company=request.env.company.name, email=request.env.company.email)
            values.update({'reply_to': values.get('email_from'), 'email_from': email_from})
        record = request.env[model_name].with_user(SUPERUSER_ID).with_context(
            mail_create_nosubscribe=True,
        ).create(values)

        if custom or meta:
            default_field = model_sudo.website_form_default_field_id
            # If there is a default field configured for this model, use it.
            # If there isn't, put the custom data in a message instead
            if default_field.name:
                custom_label = "%s\n___________\n\n" % _("Other Information:")
                if model_name == 'mail.mail':
                    custom_label = "%s\n___________\n\n" % _("This message has been posted on your website!")
                default_field_data = values.get(default_field.name, '')
                custom_content = (default_field_data + "\n\n" if default_field_data else '') \
                    + (custom_label + custom + "\n\n" if custom else '') \
                    + (self._meta_label + "\n________\n\n" + meta if meta else '')

                if default_field.ttype == 'html' or model_name == 'mail.mail':
                    custom_content = nl2br(custom_content)
                record.update({default_field.name: custom_content})
            elif hasattr(record, '_message_log'):
                render_values = {
                    'custom_label': _("Other Information:"),
                    'custom': custom,
                    'meta_label': self._meta_label,
                    'meta': meta,
                }
                custom_content = request.env['ir.qweb']._render(
                    'website.website_form_custom_log',
                    render_values
                )
                record._message_log(
                    body=custom_content,
                )

        return record.id

    # Link all files attached on the form
    def insert_attachment(self, model_sudo, id_record, files):
        if not model_sudo.env.su:
            raise ValueError("model_sudo should get passed with sudo")
        model_name = model_sudo.model
        orphan_attachment_ids = []
        record = model_sudo.env[model_name].browse(id_record)
        authorized_fields = model_sudo.with_user(SUPERUSER_ID)._get_form_writable_fields()
        for file in files:
            custom_field = file.field_name not in authorized_fields
            attachment_value = {
                'name': file.filename,
                'raw': BinaryBytes(file.read()),
                'res_model': model_name,
                'res_id': record.id,
            }
            attachment_id = request.env['ir.attachment'].sudo().create(attachment_value)
            if attachment_id and not custom_field:
                record_sudo = record.sudo()
                value = [(4, attachment_id.id)]
                if record_sudo._fields[file.field_name].type == 'many2one':
                    value = attachment_id.id
                record_sudo[file.field_name] = value
            else:
                orphan_attachment_ids.append(attachment_id.id)

        if model_name != 'mail.mail' and hasattr(record, '_message_log') and orphan_attachment_ids:
            # If some attachments didn't match a field on the model,
            # we create a mail.message to link them to the record
            record._message_log(
                attachment_ids=[(6, 0, orphan_attachment_ids)],
                body=Markup(_('<p>Attached files: </p>')),
                message_type='comment',
            )
        elif model_name == 'mail.mail' and orphan_attachment_ids:
            # If the model is mail.mail then we have no other choice but to
            # attach the custom binary field files on the attachment_ids field.
            for attachment_id_id in orphan_attachment_ids:
                record.attachment_ids = [(4, attachment_id_id)]
