from openerp import models, fields

class Actions(models.Model):
    _inherit = 'ir.actions.report.xml'

    print_report_name = fields.Char('Printed Report Name', help="This is the filename of the report going to download. Keep empty to not change the report filename. You can use a python expression with the object and time variables.")
