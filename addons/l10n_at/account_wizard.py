# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) conexus.at

from openerp import tools
from openerp.osv import osv
from openerp import addons

class AccountWizard_cd(osv.osv_memory):
	_inherit='wizard.multi.charts.accounts'
	
	_defaults = {
		'code_digits' : 0,
	}
