from odoo import fields, models

class MentalHealthNotes(models.Model):
    _name = "mental_health.notes"
    _description = "A model to be used to write mental health notes"

    name = fields.Char(string='Client Name', required=True)
    mode_of_therapy = fields.Selection(string='Mode of Therapy', required=True,
                                       selection=[('in_person', 'In Person'),
                                                  ('by_phone', 'By Phone'),
                                                  ('video_conference_online', 'Video Conference Online'),
                                                  ('email', 'Email'),
                                                  ('text', 'Text')],
                                       default='in_person',
                                       help='Select the mode of therapy.')

    date = fields.Date(string='Date Recorded', required=True, default=lambda self: fields.Date.today(), copy=False)
    icd10_codes = fields.Selection(string='ICD10 Code', required=False, copy=False,
                                   selection=[('f40.00', 'F40.00 - Agoraphobia unspecified'),
                                              ('f40.01', 'F40.01 - Agoraphobia with panic disorder')])
    description = fields.Text(string='Meeting Notes', copy=False)
