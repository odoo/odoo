# Part of Odoo. See LICENSE file for full copyright and licensing details.

import functools
import logging
import re
import requests

from odoo import _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.tools import remove_accents
from odoo.tools.translate import adapt_translated_field_value

from odoo.addons.web.icons import ICONS
from odoo.addons.html_editor.models.ir_attachment import SUPPORTED_IMAGE_MIMETYPES

logger = logging.getLogger(__name__)
diverging_history_regex = 'data-last-history-commits="([0-9,]+)"'


def get_existing_attachment(IrAttachment, vals):
    """
    Check if an attachment already exists for the same vals. Return it if
    so, None otherwise.
    """
    fields = dict(vals)
    # Falsy res_id defaults to 0 on attachment creation.
    fields['res_id'] = fields.get('res_id') or 0
    raw = fields.pop('raw', None)
    domain = [(field, '=', value) for field, value in fields.items()]
    if fields.get('type') == 'url':
        if 'url' not in fields:
            return None
        domain.append(('checksum', '=', False))
    else:
        if not raw:
            return None
        domain.append(('checksum', '=', IrAttachment._compute_checksum(raw)))
    return IrAttachment.search(domain, limit=1) or None


def attachment_create(IrAttachment, name='', data=False, url=False, res_id=False, res_model='ir.ui.view'):
    """Create and return a new attachment."""
    if name.lower().endswith('.bmp'):
        # Avoid mismatch between content type and mimetype, see original commit msg
        name = name[:-4]

    if not name and url:
        name = url.split("/").pop()

    if res_model != 'ir.ui.view' and res_id:
        res_id = int(res_id)
    else:
        res_id = False

    attachment_data = {
        'name': name,
        'public': res_model == 'ir.ui.view',
        'res_id': res_id,
        'res_model': res_model,
    }

    if data:
        attachment_data['raw'] = data
        if url:
            attachment_data['url'] = url
    elif url:
        attachment_data.update({
            'type': 'url',
            'url': url,
        })
        # The code issues a HEAD request to retrieve headers from the URL.
        # This approach is beneficial when the URL doesn't conclude with an
        # image extension. By verifying the MIME type, the code ensures that
        # only supported image types are incorporated into the data.
        response = requests.head(url, timeout=10)
        if response.status_code == 200:
            mime_type = response.headers.get('content-type')
            if mime_type in SUPPORTED_IMAGE_MIMETYPES:
                attachment_data['mimetype'] = mime_type
    else:
        raise UserError(_("You need to specify either data or url to create an attachment."))

    # Despite the user having no right to create an attachment, he can still
    # create an image attachment through some flows
    if (
        not IrAttachment.env.is_admin()
        and IrAttachment._can_bypass_rights_on_media_dialog(**attachment_data)
    ):
        attachment = IrAttachment.sudo().create(attachment_data)
        # When portal users upload an attachment with the wysiwyg widget,
        # the access token is needed to use the image in the editor. If
        # the attachment is not public, the user won't be able to generate
        # the token, so we need to generate it using sudo
        if not attachment_data['public']:
            attachment.sudo().generate_access_token()

        if IrAttachment.env.user.share:
            max_portal_file_size = int(IrAttachment.env["ir.config_parameter"].sudo().get_int(
                "html_editor.max_portal_file_size",
                100_000_000,
            ))
            if not (attachment.mimetype or '').startswith('image/'):
                raise AccessError(IrAttachment.env._("Non-internal users can only upload image."))
            if attachment.file_size >= max_portal_file_size:
                raise AccessError(IrAttachment.env._("Non-internal users can't upload large files."))
    else:
        attachment = get_existing_attachment(IrAttachment, attachment_data) \
            or IrAttachment.create(attachment_data)

    return attachment


# This method must be called in a context that has write access to the record as
# it will write to the bus.
def handle_history_divergence(record, html_field_name, vals):
    # Do not handle history divergence if the field is not in the values.
    if html_field_name not in vals:
        return
    # Do not handle history divergence if in module installation mode.
    if record.env.context.get('install_module'):
        return

    if record._fields[html_field_name].translate:
        vals[html_field_name] = adapt_translated_field_value(
            record.env, record._fields[html_field_name], vals[html_field_name],
            lambda lang, v: _handle_history_divergence(record.with_context(lang=lang), html_field_name, v),
        )
    else:
        vals[html_field_name] = _handle_history_divergence(record, html_field_name, vals[html_field_name])


def _handle_history_divergence(record, html_field_name, incoming_html):
    incoming_history_matches = re.search(diverging_history_regex, incoming_html or '')
    # When there is no incoming history id, it means that the value does not
    # comes from the odoo editor or the collaboration was not activated. In
    # project, it could come from the collaboration pad. In that case, we do not
    # handle history divergences.
    if request:
        channel = (request.db, 'editor_collaboration', record._name, html_field_name, record.id)
    if incoming_history_matches is None:
        if request:
            bus_data = {
                'model_name': record._name,
                'field_name': html_field_name,
                'res_id': record.id,
                'notificationName': 'html_field_write',
                'notificationPayload': {'last_commit_id': None},
            }
            request.env['bus.bus']._sendone(channel, 'editor_collaboration', bus_data)
        return incoming_html
    incoming_history_ids = incoming_history_matches[1].split(',')
    last_commit_id = incoming_history_ids[-1]

    bus_data = {
        'model_name': record._name,
        'field_name': html_field_name,
        'res_id': record.id,
        'notificationName': 'html_field_write',
        'notificationPayload': {'last_commit_id': last_commit_id},
    }
    if request:
        request.env['bus.bus']._sendone(channel, 'editor_collaboration', bus_data)

    if record[html_field_name]:
        server_history_matches = re.search(diverging_history_regex, record[html_field_name] or '')
        # Do not check old documents without data-last-history-commits.
        if server_history_matches:
            server_last_history_id = server_history_matches[1].split(',')[-1]
            if server_last_history_id not in incoming_history_ids:
                logger.warning('The document was already saved from someone with a different history for model %r, field %r with id %r.', record._name, html_field_name, record.id)
                raise ValidationError(_(
                    'The document was already saved from someone with a different history for model "%(model)s", field "%(field)s" with id "%(id)d".',
                    model=record._name,
                    field=html_field_name,
                    id=record.id,
                ))

    # Save only the latest id.
    return incoming_html[0:incoming_history_matches.start(1)] + last_commit_id + incoming_html[incoming_history_matches.end(1):]


def normalize_icon_text(text):
    return remove_accents(text.casefold())


# English only: the language is unknown at import time.
ICONS_INDEX = [
    (name, normalize_icon_text(f"{name} {icon['tags']._source}"))
    for name, icon in ICONS.items()
]


@functools.cache
def translated_icon_tags(lang) -> dict[str, str]:
    """Return the normalized tags of every icon, translated in ``lang``.

    Read from the po files, so the cache is safely shared by all databases.
    """
    if lang == 'en_US':
        return {}
    return {
        name: normalize_icon_text(icon['tags']._translate(lang))
        for name, icon in ICONS.items()
    }


def search_icons(env, needle=''):
    """Yield the name of every icon matching all the words of ``needle``.

    A word matches the icon name, its English tags or its tags translated in
    the user's language.  An empty needle yields every icon.
    """
    terms = normalize_icon_text(needle).split()
    if not terms:
        yield from ICONS
        return
    translated = translated_icon_tags(env.lang or 'en_US')
    for name, haystack in ICONS_INDEX:
        missing = [term for term in terms if term not in haystack]
        if missing and any(term not in translated.get(name, '') for term in missing):
            continue
        yield name
