# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.translate import adapt_translated_field_value

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
            record.env, vals[html_field_name],
            lambda lang, v: _handle_history_divergence(record.with_context(lang=lang), html_field_name, v))
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
