import sys
sys.path.insert(0, 'C:/Odoo/odoo')
import odoo
from odoo.modules.registry import Registry
from odoo import api

odoo.tools.config.parse_config(['-c', 'C:/Odoo/odoo/odoo.conf', '-d', 'odoo'])
reg = Registry('odoo')
with reg.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    menu_ids = [632, 624, 622, 688, 637, 638, 633, 693, 626, 627, 628, 629, 630, 635, 691]
    for mid in menu_ids:
        m = env['ir.ui.menu'].browse(mid)
        if m.exists():
            act = m.action
            act_type = act._name if act else 'None'
            act_id = act.id if act else None
            act_name = getattr(act, 'name', '') if act else ''
            res_model = getattr(act, 'res_model', '') if act else ''
            tag = getattr(act, 'tag', '') if act else ''
            xmlid = m.get_external_id().get(m.id, '')
            act_xmlid = act.get_external_id().get(act.id, '') if act else ''
            print(f"Menu {mid} ({xmlid}): {m.complete_name}")
            print(f"   -> Action {act_id} ({act_xmlid}) [{act_type}]: name='{act_name}', model='{res_model}', tag='{tag}'")
            print(f"   -> URL: /odoo/action-{act_id}")
