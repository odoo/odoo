from odoo import fields, models


class LoadPublicHolidayWizardLine(models.TransientModel):
    _name = "load.public.holiday.wizard.line"
    _description = "Load Public Holidays Line"
    _order = "company_id, start_date, name"

    wizard_id = fields.Many2one(
        "load.public.holiday.wizard", required=True, ondelete="cascade"
    )
    name = fields.Char(required=True)
    start_date = fields.Date(required=True)
    company_id = fields.Many2one("res.company", required=True)
