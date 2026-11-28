# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    definition = env.ref('website_forum.definition_commentator', raise_if_not_found=False)
    if definition:
        definition.write({
            'model_id': env.ref('website_forum.model_forum_post_comment').id,
            'domain': '[]',
            'batch_distinctive_field': env.ref('website_forum.field_forum_post_comment__create_uid').id,
            'batch_user_expression': 'user.id',
        })
