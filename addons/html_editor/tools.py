# Part of Odoo. See LICENSE file for full copyright and licensing details.

import functools
import logging
import re

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import remove_accents
from odoo.tools.translate import adapt_translated_field_value

from odoo.addons.web.icons import ICONS

logger = logging.getLogger(__name__)
diverging_history_regex = 'data-last-history-commits="([0-9,]+)"'


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


def normalized_icon_name(name):
    return normalize_icon_text(name.replace('_', ' '))


def icon_search_entry(name, icon):
    normalized_name = normalized_icon_name(name)
    return (
        name,
        normalized_name,
        normalize_icon_text(f"{normalized_name} {icon['tags']._source}"),
    )


# English only: the language is unknown at import time.
ICONS_INDEX = [icon_search_entry(name, icon) for name, icon in ICONS.items()]


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
    normalized_needle = normalized_icon_name(needle).strip()
    terms = normalized_needle.split()
    if not terms:
        yield from ICONS
        return
    translated = translated_icon_tags(env.lang or 'en_US')
    matching_icons = []
    for index, (name, normalized_name, haystack) in enumerate(ICONS_INDEX):
        translated_haystack = translated.get(name, '')
        if not all(term in haystack or term in translated_haystack for term in terms):
            continue
        if normalized_name == normalized_needle:
            rank = 0
        elif normalized_name.startswith(normalized_needle):
            rank = 1
        elif all(term in normalized_name for term in terms):
            rank = 2
        else:
            rank = 3
        matching_icons.append((rank, index, name))
    for _rank, _index, name in sorted(matching_icons):
        yield name
