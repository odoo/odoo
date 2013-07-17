# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA
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
from openerp.osv.orm import TransientModel

class WizardMultiChartsAccounts(TransientModel):

    _inherit ='wizard.multi.charts.accounts'

    def onchange_chart_template_id(self, cursor, uid, ids, chart_template_id=False, context=None):
        if context is None: context = {}
        res = super(WizardMultiChartsAccounts, self).onchange_chart_template_id(cursor, uid, ids,
                                                                                chart_template_id=chart_template_id,
                                                                                context=context)
        # 0 is evaluated as False in python so we have to do this
        # because original wizard test code_digits value on a float widget
        if chart_template_id:
            sterchi_template = self.pool.get('ir.model.data').get_object(cursor, uid, 'l10n_ch', 'l10nch_chart_template')
            if sterchi_template.id == chart_template_id:
                res['value']['code_digits'] = 0
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
