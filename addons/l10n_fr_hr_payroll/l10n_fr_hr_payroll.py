#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class res_company(osv.osv):
    _inherit = 'res.company'

    _columns = {
        'plafond_secu': fields.float('Plafond de la Securite Sociale', digits_compute=dp.get_precision('Payroll')),
        'nombre_employes': fields.integer('Nombre d\'employes'),
        'cotisation_prevoyance': fields.float('Cotisation Patronale Prevoyance', digits_compute=dp.get_precision('Payroll')),
        'org_ss': fields.char('Organisme de securite sociale', size=64),
        'conv_coll': fields.char('Convention collective', size=64),
    }

res_company()

class hr_contract(osv.osv):
    _inherit = 'hr.contract'

    _columns = {
        'qualif': fields.char('Qualification', size=64),
        'niveau': fields.char('Niveau', size=64),
        'coef': fields.char('Coefficient', size=64),
    }
hr_contract()

class hr_payslip(osv.osv):
    _inherit = 'hr.payslip'

    _columns = {
        'payment_mode': fields.char('Mode de paiement', size=64),
    }
hr_payslip()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
