# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv

class AccountWizard_cd(osv.osv_memory):
	_inherit='wizard.multi.charts.accounts'
		
	_defaults = {
        'code_digits' : 6,
	}
