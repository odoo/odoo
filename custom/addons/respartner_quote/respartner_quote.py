from openerp import models, fields, api, tools, _
class res_partner(models.Model):
    _inherit = 'res.partner'
    crm_lead_id = fields.Integer('CRM Lead')
    mom_company_id = fields.Many2one('res.partner', string="Mother Company")

    