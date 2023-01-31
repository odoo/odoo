# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_eg_branch_id = fields.Many2one('res.partner', string='Branch', copy=False,
                                        help="Address of the subdivision of the company.  You can just put the "
                                             "company partner if this is used for the main branch.")
    l10n_eg_activity_type_id = fields.Many2one('l10n_eg_edi.activity.type', 'ETA Activity Code', copy=False,
                                               help='This is the activity type of the branch according to Egyptian Tax Authority')
    l10n_eg_branch_identifier = fields.Char('ETA Branch ID', copy=False,
                                            help="This number can be found on the taxpayer profile on the eInvoicing portal. ")
