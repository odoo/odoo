# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    aec_report_changes_impact_journal_id = fields.Many2one('account.journal',
        string='Equity Changes Correction Journal', help='Journal for Impact of changes in accounting policies and error correction entries')
    
    
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    aec_report_changes_impact_journal_id = fields.Many2one('account.journal', related='company_id.aec_report_changes_impact_journal_id',
        string='Equity Changes Correction Journal', help='Journal for Impact of changes in accounting policies and error correction entries', readonly=False)
    
