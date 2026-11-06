import sys
sys.path.insert(0, 'C:/Odoo/odoo')
import odoo
from odoo.modules.registry import Registry
from odoo import api

odoo.tools.config.parse_config(['-c', 'C:/Odoo/odoo/odoo.conf', '-d', 'odoo'])
reg = Registry('odoo')
with reg.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    years = env['university.academic.year'].search([])
    for y in years:
        print(f"Year {y.id}: {y.name} | current={y.current} | state={y.state} | {y.date_start} to {y.date_end}")
        for s in y.semester_ids:
            print(f"   Semester {s.id}: {s.name} ({s.semester_type}) | is_active={s.is_active} | {s.date_start} to {s.date_end}")
