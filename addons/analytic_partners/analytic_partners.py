from osv import osv, fields

class analytic_partners_account_analytic_account(osv.osv) :
	_name = 'account.analytic.account'
	_inherit = 'account.analytic.account'
	_columns = {
		'address_ids' : fields.many2many('res.partner.address', 'account_partner_rel', 'account_id', 'address_id', 'Partners Contacts'),
	}
	
analytic_partners_account_analytic_account()
