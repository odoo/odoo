from osv import fields,osv


class report_workcenter_load(osv.osv):
	_name="report.workcenter.load"
	_description="Workcenter Load"
	_auto = False
	_columns = {
		'name': fields.char('Week', size=64, required=True),
		'workcenter_id': fields.many2one('mrp.workcenter', 'Workcenter', required=True),
		'cycle': fields.float('Nbr of cycle'),
		'hour': fields.float('Nbr of hour'),
	}
	def init(self, cr):
		cr.execute("""
			create or replace view report_workcenter_load as (
				SELECT
					min(wl.id) as id,
					to_char(stock_move.create_date,'YYYY:IW') as name,
					SUM(wl.hour) AS hour,
					SUM(wl.cycle) AS cycle,
					wl.workcenter_id as workcenter_id
				FROM
					mrp_production_workcenter_line wl
				GROUP BY
					wl.workcenter_id,
					to_char(stock_move.create_date,'YYYY:IW')
			)""")
report_workcenter_load()

class report_mrp_inout(osv.osv):
	_name="report.mrp.inout"
	_description="Stock value variation"
	_auto = False
	_rec_name = 'date'
	_columns = {
		'date': fields.char('Week', size=64, required=True),
		'value': fields.float('Stock value', required=True),
	}
	def init(self, cr):
		cr.execute("""
			create or replace view report_mrp_inout as (
				select
					min(sm.id) as id,
					to_char(sm.date_planned,'YYYY:IW') as date,
					sum(case when (sl.usage='internal') then
						pt.standard_price * sm.product_qty
					else
						0.0
					end - case when (sl2.usage='internal') then
						pt.standard_price * sm.product_qty
					else
						0.0
					end) as value
				from
					stock_move sm
				left join product_product pp
					on (pp.id = sm.product_id)
				left join product_template pt
					on (pt.id = pp.product_tmpl_id)
				left join stock_location sl
					on ( sl.id = sm.location_id)
				left join stock_location sl2
					on ( sl2.id = sm.location_dest_id)
				where
					sm.state in ('waiting','confirmed','assigned')
				group by
					to_char(sm.date_planned,'YYYY:IW')
			)""")
report_mrp_inout()

