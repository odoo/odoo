from odoo import models, fields

class MasterContract(models.Model):
    _name = "master_contract"
    _description = "Description of the Master Contract model"
    name = fields.Char()
    category = fields.Selection([('trading', 'Trading'), ('supplying', 'Supplying')
                             ], 'Category'
                             )
    type = fields.Selection([('efet', 'EFET'), ('other', 'OTHER')],
                            'Type')
    status = fields.Selection([('initial', 'Initial'), ('executing', 'Executing'),('finished', 'Finished')], 'Status')
    company_id = fields.Many2one('company', string='Company')
    contract_ids = fields.One2many('contract', 'master_contract_id', string='Contracts')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')