# -*- coding: utf-8 -*-

from openerp import api, fields, models


class AccountSequenceInstaller(models.TransientModel):
    _name = 'account.sequence.installer'
    _inherit = 'res.config.installer'

    name = fields.Char(required=True, default='Internal Sequence Journal')
    prefix = fields.Char(help="Prefix value of the record for the sequence")
    suffix = fields.Char(help="Suffix value of the record for the sequence")
    number_next = fields.Integer(string='Next Number', required=True, default=1, help="Next number of this sequence")
    number_increment = fields.Integer(string='Increment Number', required=True, default=1, help="The next number of the sequence will be incremented by this number")
    padding = fields.Integer(string='Number padding', required=True, default=0, help="Odoo will automatically adds some '0' on the left of the 'Next Number' to get the required padding size.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('ir.sequence'))

    @api.multi
    def execute(self):
        self.ensure_one()
        if self.company_id:
            company_id = self.company_id.id,
            search_criteria = [('company_id', '=', company_id)]
        else:
            company_id = False
            search_criteria = []
        vals = {
            'id': 'internal_sequence_journal',
            'code': 'account.journal',
            'name': self.name,
            'prefix': self.prefix,
            'suffix': self.suffix,
            'number_next': self.number_next,
            'number_increment': self.number_increment,
            'padding' : self.padding,
            'company_id': company_id,
        }

        ir_seq = self.env['ir.sequence'].create(vals)
        res =  super(AccountSequenceInstaller, self).execute()
        Journal = self.env['account.journal']
        journals = Journal.search(search_criteria)
        for journal in journals:
            if not journal.internal_sequence_id:
                Journal += journal
        Journal.write({'internal_sequence_id': ir_seq.id})
        self.env['ir.values'].set(key='default', key2=False, name='internal_sequence_id', models=[('account.journal', False)], value=ir_seq.id)
        return res
