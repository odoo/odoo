from odoo import fields, models


class MentalHealthNotes(models.Model):
    _name = "mental_health.notes"
    _description = "A model to be used to write mental health notes"

    name = fields.Char(string='Client Name', required=True)
    description = fields.Text(string='Meeting Notes', copy=False)
    date = fields.Date(string='Date Recorded', required=True, default=lambda self: fields.Date.today(), copy=False)
    service_type = fields.Selection(string='Service Provided', required=True,
                                    selection=[('intake', 'Intake'),
                                               ('individual_therapy', 'Individual Therapy')],
                                    default='individual_therapy',
                                    help='Select the type of service provided.')
    icd10_codes = fields.Selection(string='ICD10 Code', required=False, copy=False,
                                   selection=[('f40.00', 'F40.00 - Agoraphobia unspecified'),
                                              ('f40.01', 'F40.01 - Agoraphobia with panic disorder')])
    homework = fields.Text(string='Homework Assignment')
