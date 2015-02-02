from openerp.osv import fields, osv

class stock_warehouse_orderpoint(osv.osv):
    _inherit = "stock.warehouse.orderpoint"

    _columns = {
        'calendar_id': fields.many2one('resource.calendar', 'Calendar',
                                       help="In the calendar you can define the days that the goods will be delivered.  That way the scheduler will only take into account the goods needed until the second delivery and put the procurement date as the first delivery.  "),
        'purchase_calendar_id': fields.many2one('resource.calendar', 'Purchase Calendar'),
        'last_execution_date': fields.datetime('Last Execution Date', readonly=True),
    }
