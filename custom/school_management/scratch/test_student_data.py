import sys
sys.path.insert(0, r"C:\Odoo\odoo")
import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

config_file = r"C:\Odoo\odoo\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file])

registry = Registry("odoo")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    card = env["university.report.card"].browse(105)
    student = card.student_id
    print("Student:", student.name)
    all_cards = student.report_card_ids.sorted(lambda c: (c.academic_year_id.date_start or c.academic_year_id.name, c.semester_id.name))
    print("Student cards:", [(c.id, c.academic_year_id.name, c.semester_id.name, len(c.line_ids)) for c in all_cards])
    
    # Check years
    years = all_cards.mapped("academic_year_id")
    print("Years:", [y.name for y in years])
