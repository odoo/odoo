# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo.tools.misc import OrderedSet


def filter_messages_exist(env, messages):
    ids_by_model = defaultdict(OrderedSet)
    prefetch_ids_by_model = defaultdict(OrderedSet)
    prefetch_messages = messages | messages.browse(messages._prefetch_ids)
    for message in prefetch_messages.filtered(lambda m: m.model and m.res_id):
        target = ids_by_model if message in messages else prefetch_ids_by_model
        target[message.model].add(message.res_id)
    records_by_model_name = {
        model_name: env[model_name]
        .browse(ids)
        .with_prefetch(tuple(ids_by_model[model_name] | prefetch_ids_by_model[model_name]))
        for model_name, ids in ids_by_model.items() if env[model_name].browse(ids).exists()
    }
    record_by_message = {
        message: env[message.model]
        .browse(message.res_id)
        .with_prefetch(records_by_model_name[message.model]._prefetch_ids)
        for message in messages.filtered(
            lambda m:
                m.model and m.res_id and
                m.model in records_by_model_name and
                m.res_id in records_by_model_name[m.model].ids
            )
    }
    return messages.browse([msg.id for msg in record_by_message])
