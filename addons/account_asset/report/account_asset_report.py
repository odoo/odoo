import tools
from osv import fields,osv

class asset_asset_report(osv.osv):
    _name = "asset.asset.report"
    _description = "Assets Analysis"
    _auto = False
    _columns = {
    	'date': fields.date('Asset Date', readonly=True),
	'asset_id': fields.many2one('account.asset.asset',string='Asset'),
#	'asset_category': fields.many2one('account.asset.category',string='Asset category'),
	'state': fields.related('asset_id','state',type='char', string='State', readonly=True),
    }
    def init(self, cr):
	tools.drop_view_if_exists(cr, 'asset_asset_report')
 	cr.execute("""
	    create or replace view asset_asset_report as (
		 select id as id,
		        asset_id as asset_id,
			date as date,
			state as state
		 from
	   	    account_move_line )""")
	
asset_asset_report()
