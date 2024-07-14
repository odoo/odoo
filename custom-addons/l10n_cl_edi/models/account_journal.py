# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_cl_point_of_sale_type = fields.Selection([
        ('manual', 'Manual'),
        ('online', 'Online'),
    ], string='Point Of Sale Type', help='You must select "Online" for journals with documents that need to be\n'
                                         'sent to SII automatically. In this case you must upload a CAF file for each\n'
                                         'type of document you will use in this journal.\n'
                                         'You must select "Manual" if you are either a user of "Facturación MiPyme"\n'
                                         '(free SII\'s website invoicing system) or if you have already generated\n'
                                         'those documents using a different system in the past, and you want to\n'
                                         'register them in Odoo now.', copy=False)
    l10n_cl_point_of_sale_number = fields.Integer(
        'Point Of Sale Number', help='This number is needed only if provided by SII.', copy=False)
    l10n_cl_point_of_sale_name = fields.Char(
        'Point Of Sale Name',
        help='This is the name that you want to assign to your point of sale. It is not mandatory.', copy=False)

    @api.onchange('type')
    def _onchange_type(self):
        self.l10n_cl_point_of_sale_type = ('online' if self.type == 'sale' and self.l10n_latam_use_documents and
                                           self.country_code == 'CL'else False)
