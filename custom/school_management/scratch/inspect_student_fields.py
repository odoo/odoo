import sys
sys.path.insert(0, r"C:\Odoo\odoo")
import odoo
from odoo.tools import config
config.parse_config(['-c', r'C:\Odoo\odoo\odoo.conf', '-d', 'odoo'])

registry = odoo.modules.registry.Registry('odoo')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    # Check if school_management is loaded
    print("Installed modules with school:")
    mods = env['ir.module.module'].search([('name', 'like', 'school%')])
    for m in mods:
        print(f"  {m.name}: {m.state}")

    Student = env['university.student']
    print("\nAll fields on university.student in env:")
    for k in sorted(Student._fields.keys()):
        if 'khmer' in k or 'name' in k:
            f = Student._fields[k]
            print(f"  {k}: type={f.type}, compute={f.compute}, manual={getattr(f, 'manual', None)}")
