# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2008 P. Christeas. All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import netsvc
from osv import osv, fields

class fiscal_print(osv.osv):
  _name = 'account.fiscalgr.print'
  _inherit = ''
  _columns = {
      'hash': fields.char('Secure hash', size=40, readonly=True,),
      'date': fields.char('Print date', size=10, readonly=True,),
      'state': fields.selection([('unknown','Unknown'),
           ('queued','Queued'), ('printed','Printed'), ('error','Failed')],
	   'State', readonly = True, required = True),
      'machine_id': fields.char('Machine ID', size=12, readonly=True,),
      'day_no': fields.integer('Daily sequence', readonly=True),
      'total_no': fields.integer('Total sequence', readonly=True),
      'cups_jobid': fields.integer('Job ID', readonly=True, required=True, help="CUPS job id"),
      'name': fields.char('Title',size=200,required=True, readonly=True,help="Title of the CUPS job, typically the invoice reference."),
      'cups_msg': fields.text('CUPS message',help="This is the message returned by cups, if the printing fails.", readonly=True),
      'report': fields.many2one('ir.actions.report.xml', 'Report', required=True,readonly=True),
  }
  _defaults = {
	'state' : lambda *a: 'unknown',
  }
  
  def _print_fiscal(self,cr,uid,report_id,title,format,content,printer=False,copies=1,context=None):
	import tempfile
	import os
	if not printer:
		raise Exception(_('No printer specified for report'))
	if not copies:
		copies=1
	(fileno, fp_name) = tempfile.mkstemp('.'+format, 'openerp_')
	fp = file(fp_name, 'wb+')
	fp.write(content.encode('iso8859-7'))
	fp.close()
	os.close(fileno)
	PRINTER='Forol2'
	try:
		import cups
	except:
		raise Exception(_('Cannot talk to cups, please install pycups'))
	ccon = cups.Connection()
	#attrs=ccon.getPrinterAttributes(name=PRINTER)
	#print "Located \"%s\" at a v%s CUPS server" %(attrs['printer-make-and-model'],attrs['cups-version'])
	#print 'Trying to print %s at %s'%(fp_name,PRINTER)
	job = ccon.printFile(printer,fp_name,title,{'copies': str(copies)})
	os.unlink(fp_name)
	if job:
		print 'Created job %d'% job
		fprn=self.create(cr,uid,{'cups_jobid':job,'name':title,'report':report_id, 'state': 'queued'},context)
		self._set_pooler_active(cr,uid,True)
		return True
	else:
		raise Exception(_('Cannot print at printer %s')%printer)
		return False

  def print_invoice(self,cr,uid,inv_data,inv_model,inv_title, inv_report, context):
	logger=netsvc.Logger()
	logger.notifyChannel("fiscalgr", netsvc.LOG_DEBUG, 'printing one %s invoice '%(inv_report))
	report_obj=self.pool.get('ir.actions.report.xml')
	rep= report_obj.read(cr,uid,inv_report,[])
	if (rep['model']!=inv_model or rep['report_type'] != 'txt'):
		raise osv.except_osv(_('Cannot print!'), _('The set invoice at %d is not valid for this object.')%inv_report)
	try:
		obj = netsvc.LocalService('report.'+rep['report_name'])
		if not obj:
			raise Exception('cannot get object report.%s'% rep['report_name'])
		data = { 'model' : inv_model, 'id':inv_data['id'], 'report_type': rep['report_type']}
		(result, format) = obj.create(cr, uid, [inv_data['id'],], data, context=context)
		if (format != 'txt'):
			raise Exception("Invoice format is not txt, strange")
		# print result
		return self._print_fiscal(cr,uid,inv_report,title=inv_title,format=format,
			content=result.decode('utf-8'),printer=rep['printer'],
			copies=rep['copies'],context=context)

		#self._reports[id]['result'] = result
		#self._reports[id]['format'] = format
		#self._reports[id]['state'] = True
	except Exception, exception:
		import traceback
		import sys
		tb_s = reduce(lambda x, y: x+y, traceback.format_exception(
			sys.exc_type, sys.exc_value, sys.exc_traceback))
		logger = netsvc.Logger()
		logger.notifyChannel('web-services', netsvc.LOG_ERROR,
			'Exception: %s\n%s' % (str(exception), tb_s))
		#self._reports[id]['exception'] = exception
		#self._reports[id]['state'] = True
		raise
		#return False
	return False

  def check_results(self,cr,uid,context=None):
	logger = netsvc.Logger()
	logger.notifyChannel('fiscalgr-prints', netsvc.LOG_DEBUG,
		'Checking for pending fiscal prints.')
	if not context:
            context={}
	
	try:
		import cups
	except:
		raise Exception(_('Cannot talk to cups, please install pycups'))

	ccon = cups.Connection()
	open_prints=self.search(cr,uid,[('state','=','queued')])
	if not open_prints:
		self._set_pooler_active(cr,uid,False)
		return
	
	logger.notifyChannel('fiscalgr-prints', netsvc.LOG_DEBUG,
		'Found %d pending fiscal prints.'%len(open_prints))
	
	prints = self.read(cr,uid,open_prints,['state','title','cups_jobid'])
	
	pending_jobs = len(prints)
	for pjob in prints:
		jats = ccon.getJobAttributes(pjob['cups_jobid'])
		ndata = {}
		print "Job %d attributes" % pjob['cups_jobid'],jats
		if 'job-printer-state-message' in jats:
			jpsm = jats['job-printer-state-message']
		else:
			jpsm = ''
		
		if jats['job-state'] == cups.IPP_OK:
			pending_jobs -= 1
			if jpsm.startswith('eafdSigns-1:'):
				ndata['hash'] = jpsm[12:]
			ndata['state'] = 'printed'
			#TODO more fields
		else:
			# job is still pending
			ndata['cups_msg'] = jpsm
			
		if ndata:
			self.write(cr,uid,pjob['id'],ndata)
	
	self._set_pooler_active(cr,uid,(pending_jobs > 0))
	return True
	
  def _set_pooler_active(self,cr,uid,active=True):
		'''We ask the pooler to periodically check our jobs
		'''
		logger = netsvc.Logger()
		obj = self.pool.get('ir.cron')
		pids = obj.search(cr,uid,[('model','=',self._name),('function','=','check_results')])
		
		if len(pids) != 1 :
			logger.notifyChannel('fiscalgr-prints', netsvc.LOG_WARNING,
				'Found %d pooler jobs instead of 1.'%len(pids))
		
		print "trying to update the state"
		obj.write(cr,uid,pids[0],{'active': active})
		return True
fiscal_print()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

