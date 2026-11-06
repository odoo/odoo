import sys
sys.path.insert(0, 'C:/Odoo/odoo')
import odoo
from odoo.modules.registry import Registry
from odoo import api

odoo.tools.config.parse_config(['-c', 'C:/Odoo/odoo/odoo.conf', '-d', 'odoo'])
reg = Registry('odoo')
with reg.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    menus = env['ir.ui.menu'].search([('name', 'ilike', 'Configuration')])
    for m in menus:
        xmlid = m.get_external_id().get(m.id, '')
        print(f"Menu ID {m.id} ({xmlid}): {m.complete_name} | groups={[g.name for g in m.group_ids]}")
