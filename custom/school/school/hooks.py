# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp import api


def post_init_hook(cr, registry):

    env = api.Environment(cr, SUPERUSER_ID, {})
    rule_id = env.ref('base.res_users_rule')
    cr.execute("""UPDATE ir_rule SET active = False
                WHERE id = %s""", (rule_id.id,))
