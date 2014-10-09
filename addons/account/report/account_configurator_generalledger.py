# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields


class AccountReportsConfiguratorGeneralLedger(models.TransientModel):
    _name = 'configurator.generalledger'
    _inherit = 'configurator.account'

    landscape = fields.Boolean(default=True)
    initial_balance = fields.Boolean(default=False)
    amount_currency = fields.Boolean(default=True)
    sortby = fields.Char(default='sort_date')

    def _specific_format(self, form_data):
        if form_data['landscape'] is False:
            form_data.pop('landscape')
        else:
            self.env.context['landscape'] = form_data['landscape']
        return form_data
