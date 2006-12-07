import time
import netsvc
from osv import fields,osv,orm
import ir
from mx import DateTime


class edi_log(osv.osv):
	_name = "edi.log"
	_description = "EDI log"
	_columns = {	'name': fields.char('Log name', size=32, required=True),
					'log_line': fields.one2many('edi.log.line', 'log_id', 'Log Lines', readonly=True, states={'draft':[('readonly', False)]}),
				}

	_defaults = {	'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
				}

edi_log()


class edi_log_line(osv.osv):
	_name = "edi.log.line"
	_description = "EDI Log Line"
	_columns = {	'log_id': fields.many2one('edi.log', 'Log Ref'),
					'name': fields.char('Name', size=64, required=True),
					'logdesc': fields.text('Description'),
					'sender': fields.many2one('res.partner', 'Partner', readonly=True),
					'timestamp': fields.char('Order date', size=13),
					'order_num': fields.char('Edi Order Id', size=15),
				}
	_defaults = {	'name': lambda *a: 'logline',
				}

edi_log_line()

