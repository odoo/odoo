# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2013-2014 7Gates Interactive Technologies 
#                           <http://www.7gates.co>
#                 @author Erdem Uney
#   
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _

class res_company(osv.osv):
    
    _inherit = "res.company"
    
    _columns = {
        'vat_dept': fields.related('partner_id', 'vat_dept', string="Tax Department", type="char", size=32),
        }
        
    def onchange_footer(self, cr, uid, ids, custom_footer, phone, fax, email, website, vat_dept, vat, company_registry, bank_ids, context=None):
        if custom_footer:
            return {}

        # first line (notice that missing elements are filtered out before the join)
        res = ' | '.join(filter(bool, [
            phone            and '%s: %s' % (_('Phone'), phone),
            fax              and '%s: %s' % (_('Fax'), fax),
            email            and '%s: %s' % (_('Email'), email),
            website          and '%s: %s' % (_('Website'), website),
            vat_dept         and '%s: %s' % (_('TID'), vat_dept),
            vat              and '%s: %s' % (_('TIN'), vat),
            company_registry and '%s: %s' % (_('Reg'), company_registry),
        ]))
        # second line: bank accounts
        res_partner_bank = self.pool.get('res.partner.bank')
        account_data = self.resolve_2many_commands(cr, uid, 'bank_ids', bank_ids, context=context)
        account_names = res_partner_bank._prepare_name_get(cr, uid, account_data, context=context)
        if account_names:
            title = _('Bank Accounts') if len(account_names) > 1 else _('Bank Account')
            res += '\n%s: %s' % (title, ', '.join(name for id, name in account_names))

        return {'value': {'rml_footer': res, 'rml_footer_readonly': res}}
