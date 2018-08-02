

from openerp import models, fields, api


class res_company(models.Model):
    _inherit = 'res.company'
    
    intrastat_custom_id = fields.Many2one(
        'account.intrastat.custom', string='Custom'
        )
    
