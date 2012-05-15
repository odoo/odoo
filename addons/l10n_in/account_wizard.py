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
import tools
from osv import  osv
from osv import fields, osv

class account_wizard(osv.osv_memory):
    _inherit ='wizard.multi.charts.accounts'
    _columns = {
        'sales_tax_central': fields.boolean('Sales tax central'),     
        'vat_resellers': fields.boolean('VAT resellers'),
        'service_tax': fields.boolean('Service tax'),
        'excise_duty': fields.boolean('Excise duty'),
    }    


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
