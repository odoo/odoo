import sys
sys.path.insert(0, r"C:\Odoo\odoo")
import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

config_file = r"C:\Odoo\odoo\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file])

# Update module school_management
registry = Registry("odoo")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = env["ir.module.module"].search([("name", "=", "school_management")])
    print("Module state:", module.state)
    module.button_immediate_upgrade()
    print("Module upgraded successfully!")
