from odoo import api,fields,models

class HospitalPatient(models.Model):
    _name = "hospital.patient"
    _description = "Hospital patient"

    name = fields.Char(string='Name')
    age=fields.Integer(string='Age')
    # feild selector [('key','value'),string as name/gender]
    gender=fields.Selection([('male','male'),('female','Female')],string='Gender')