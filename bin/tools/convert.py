#----------------------------------------------------------
# Convert 
#----------------------------------------------------------
import re
import StringIO,xml.dom.minidom
import osv,ir,pooler

import csv
import os.path
import misc
import netsvc

from config import config


# Number of imported lines between two commit (see convert_csv_import()):
COMMIT_STEP = 500 


class ConvertError(Exception):
	def __init__(self, doc, orig_excpt):
		self.d = doc
		self.orig = orig_excpt
	
	def __str__(self):
		return 'Exception:\n\t%s\nUsing file:\n%s' % (self.orig, self.d)

def _eval_xml(self,node, pool, cr, uid, idref):
	if node.nodeType == node.TEXT_NODE:
		return node.data.encode("utf8")
	elif node.nodeType == node.ELEMENT_NODE:
		if node.nodeName in ('field','value'):
			t = node.getAttribute('type') or 'char'
			if len(node.getAttribute('search')):
				f_search = node.getAttribute("search").encode('utf-8')
				f_model = node.getAttribute("model").encode('ascii')
				f_use = node.getAttribute("use").encode('ascii')
				f_name = node.getAttribute("name").encode('utf-8')
				if len(f_use)==0:
					f_use = "id"
				q = eval(f_search, idref)
				ids = pool.get(f_model).search(cr, uid, q)
				if f_use<>'id':
					ids = map(lambda x: x[f_use], pool.get(f_model).read(cr, uid, ids, [f_use]))
				_cols = pool.get(f_model)._columns
				if (f_name in _cols) and _cols[f_name]._type=='many2many':
					return ids
				f_val = False
				if len(ids):
					f_val = ids[0]
					if isinstance(f_val, tuple):
						f_val = f_val[0]
				return f_val
			a_eval = node.getAttribute('eval')
			if len(a_eval):
				import time
				idref['time'] = time
				idref['ref'] = lambda x: self.id_get(cr, False, x)
				try:
					import pytz
				except:
					logger = netsvc.Logger()
					logger.notifyChannel("init", netsvc.LOG_INFO, 'could not find pytz library')
					class pytzclass(object):
						all_timezones=[]
					pytz=pytzclass()
				idref['pytz'] = pytz
				return eval(a_eval, idref)
			if t == 'xml':
				def _process(s, idref):
					m = re.findall('[^%]%\((.*?)\)[ds]', s)
					for id in m:
						if not id in idref:
							idref[id]=self.id_get(cr, False, id)
					return s % idref
				txt = '<?xml version="1.0"?>\n'+_process("".join([i.toxml().encode("utf8") for i in node.childNodes]), idref)
#				txt = '<?xml version="1.0"?>\n'+"".join([i.toxml().encode("utf8") for i in node.childNodes]) % idref

				return txt
			if t in ('char', 'int', 'float'):
				d = ""
				for n in [i for i in node.childNodes]:
					d+=str(_eval_xml(self,n,pool,cr,uid,idref))
				if t == 'int':
					d = d.strip()
					if d=='None':
						return None
					else:
						d=int(d.strip())
				elif t=='float':
					d=float(d.strip())
				return d
			elif t in ('list','tuple'):
				res=[]
				for n in [i for i in node.childNodes if (i.nodeType == i.ELEMENT_NODE and i.nodeName=='value')]:
					res.append(_eval_xml(self,n,pool,cr,uid,idref))
				if t=='tuple':
					return tuple(res)
				return res
		elif node.nodeName=="getitem":
			for n in [i for i in node.childNodes if (i.nodeType == i.ELEMENT_NODE)]:
				res=_eval_xml(self,n,pool,cr,uid,idref)
			if not res:
				raise LookupError
			elif node.getAttribute('type') in ("int", "list"):
				return res[int(node.getAttribute('index'))]
			else:
				return res[node.getAttribute('index').encode("utf8")]
		elif node.nodeName=="function":
			args = []
			a_eval = node.getAttribute('eval')
			if len(a_eval):
				idref['ref'] = lambda x: self.id_get(cr, False, x)
				args = eval(a_eval, idref)
			for n in [i for i in node.childNodes if (i.nodeType == i.ELEMENT_NODE)]:
				args.append(_eval_xml(self,n, pool, cr, uid, idref))
			model = pool.get(node.getAttribute('model'))
			method = node.getAttribute('name')
			res = getattr(model, method)(cr, uid, *args)
			return res

escape_re = re.compile(r'(?<!\\)/')
def escape(x):
	return x.replace('\\/', '/')

class xml_import(object):

	def _test_xml_id(self, xml_id):
		id = xml_id
		if '.' in xml_id:
			base, id = xml_id.split('.')
		if len(id) > 64:
			self.logger.notifyChannel('init', netsvc.LOG_ERROR, 'id: %s is to long (max: 64)'%xml_id)
	def _tag_delete(self, cr, rec, data_node=None):
		d_model = rec.getAttribute("model")
		d_search = rec.getAttribute("search")
		ids = self.pool.get(d_model).search(cr,self.uid,eval(d_search))
		if len(ids):
			self.pool.get(d_model).unlink(cr, self.uid, ids)
			#self.pool.get('ir.model.data')._unlink(cr, self.uid, d_model, ids, direct=True)
		return False

	def _tag_report(self, cr, rec, data_node=None):
		res = {}
		for dest,f in (('name','string'),('model','model'),('report_name','name')):
			res[dest] = rec.getAttribute(f).encode('utf8')
			assert res[dest], "Attribute %s of report is empty !" % (f,)
		for field,dest in (('rml','report_rml'),('xml','report_xml'),('xsl','report_xsl')):
			if rec.hasAttribute(field):
				res[dest] = rec.getAttribute(field).encode('utf8')
		if rec.hasAttribute('auto'):
			res['auto'] = eval(rec.getAttribute('auto'))
		if rec.hasAttribute('sxw'):
			sxw_content = misc.file_open(rec.getAttribute('sxw')).read()
			res['report_sxw_content'] = sxw_content
		if rec.hasAttribute('header'):
			res['header'] = eval(rec.getAttribute('header'))
		res['multi'] = rec.hasAttribute('multi') and  eval(rec.getAttribute('multi'))
		xml_id = rec.getAttribute('id').encode('utf8')
		self._test_xml_id(xml_id)
		id = self.pool.get('ir.model.data')._update(cr, self.uid, "ir.actions.report.xml", self.module, res, xml_id, mode=self.mode)
		self.idref[xml_id] = id
		if not rec.hasAttribute('menu') or eval(rec.getAttribute('menu')):
			keyword = str(rec.getAttribute('keyword') or 'client_print_multi')
			keys = [('action',keyword),('res_model',res['model'])]
			value = 'ir.actions.report.xml,'+str(id)
			replace = rec.hasAttribute('replace') and rec.getAttribute("replace")
			self.pool.get('ir.model.data').ir_set(cr, self.uid, 'action', keyword, res['name'], [res['model']], value, replace=replace, isobject=True, xml_id=xml_id)
		return False

	def _tag_function(self, cr, rec, data_node=None):
		_eval_xml(self,rec, self.pool, cr, self.uid, self.idref)
		return False

	def _tag_wizard(self, cr, rec, data_node=None):
		string = rec.getAttribute("string").encode('utf8')
		model = rec.getAttribute("model").encode('utf8')
		name = rec.getAttribute("name").encode('utf8')
		xml_id = rec.getAttribute('id').encode('utf8')
		self._test_xml_id(xml_id)
		multi = rec.hasAttribute('multi') and  eval(rec.getAttribute('multi'))
		res = {'name': string, 'wiz_name': name, 'multi':multi}

		id = self.pool.get('ir.model.data')._update(cr, self.uid, "ir.actions.wizard", self.module, res, xml_id, mode=self.mode)
		self.idref[xml_id] = id
		# ir_set
		if not rec.hasAttribute('menu') or eval(rec.getAttribute('menu')):
			keyword = str(rec.getAttribute('keyword') or 'client_action_multi')
			keys = [('action',keyword),('res_model',model)]
			value = 'ir.actions.wizard,'+str(id)
			replace = rec.hasAttribute('replace') and rec.getAttribute("replace")
			self.pool.get('ir.model.data').ir_set(cr, self.uid, 'action', keyword, string, [model], value, replace=replace, isobject=True, xml_id=xml_id)
		return False

	def _tag_act_window(self, cr, rec, data_node=None):
		name = rec.hasAttribute('name') and rec.getAttribute('name').encode('utf-8')
		xml_id = rec.getAttribute('id').encode('utf8')
		self._test_xml_id(xml_id)
		type = rec.hasAttribute('type') and rec.getAttribute('type').encode('utf-8') or 'ir.actions.act_window'
		view_id = False
		if rec.hasAttribute('view'):
			view_id = self.id_get(cr, 'ir.actions.act_window', rec.getAttribute('view').encode('utf-8'))
		domain = rec.hasAttribute('domain') and rec.getAttribute('domain').encode('utf-8')
		context = rec.hasAttribute('context') and rec.getAttribute('context').encode('utf-8') or '{}'
		res_model = rec.getAttribute('res_model').encode('utf-8')
		src_model = rec.hasAttribute('src_model') and rec.getAttribute('src_model').encode('utf-8')
		view_type = rec.hasAttribute('view_type') and rec.getAttribute('view_type').encode('utf-8') or 'form'
		view_mode = rec.hasAttribute('view_mode') and rec.getAttribute('view_mode').encode('utf-8') or 'tree,form'
		usage = rec.hasAttribute('usage') and rec.getAttribute('usage').encode('utf-8')

		res = {'name': name, 'type': type, 'view_id': view_id, 'domain': domain, 'context': context, 'res_model': res_model, 'src_model': src_model, 'view_type': view_type, 'view_mode': view_mode, 'usage': usage }

		id = self.pool.get('ir.model.data')._update(cr, self.uid, 'ir.actions.act_window', self.module, res, xml_id, mode=self.mode)
		self.idref[xml_id] = id

		if src_model:
			keyword = 'client_action_relate'
			keys = [('action', keyword), ('res_model', res_model)]
			value = 'ir.actions.act_window,'+str(id)
			replace = rec.hasAttribute('replace') and rec.getAttribute('replace')
			self.pool.get('ir.model.data').ir_set(cr, self.uid, 'action', keyword, xml_id, [src_model], value, replace=replace, isobject=True, xml_id=xml_id)
		return False

	def _tag_ir_set(self, cr, rec, data_node=None):
		if not self.mode=='init':
			return False
		res = {}
		for field in [i for i in rec.childNodes if (i.nodeType == i.ELEMENT_NODE and i.nodeName=="field")]:
			f_name = field.getAttribute("name").encode('utf-8')
			f_val = _eval_xml(self,field,self.pool, cr, self.uid, self.idref)
			res[f_name] = f_val
		self.pool.get('ir.model.data').ir_set(cr, self.uid, res['key'], res['key2'], res['name'], res['models'], res['value'], replace=res.get('replace',True), isobject=res.get('isobject', False), meta=res.get('meta',None))
		return False

	def _tag_workflow(self, cr, rec, data_node=None):
		model = str(rec.getAttribute('model'))
		wf_service = netsvc.LocalService("workflow")
		wf_service.trg_validate(self.uid, model,
			self.id_get(cr, model, rec.getAttribute('ref')),
			str(rec.getAttribute('action')), cr)
		return False

	def _tag_menuitem(self, cr, rec, data_node=None):
		rec_id = rec.getAttribute("id").encode('ascii')
		self._test_xml_id(rec_id)
		m_l = map(escape, escape_re.split(rec.getAttribute("name").encode('utf8')))
		pid = False
		for idx, menu_elem in enumerate(m_l):
			if pid:
				cr.execute('select id from ir_ui_menu where parent_id=%d and name=%s', (pid, menu_elem))
			else:
				cr.execute('select id from ir_ui_menu where parent_id is null and name=%s', (menu_elem,))
			res = cr.fetchone()
			if idx==len(m_l)-1:
				# we are at the last menu element/level (it's a leaf)
				values = {'parent_id': pid,'name':menu_elem}

				if rec.hasAttribute('action'):
					a_action = rec.getAttribute('action').encode('utf8')
					a_type = rec.getAttribute('type').encode('utf8') or 'act_window'
					icons = {
						"act_window": 'STOCK_NEW',
						"report.xml": 'STOCK_PASTE',
						"wizard": 'STOCK_EXECUTE',
					}
					values['icon'] = icons.get(a_type,'STOCK_NEW')
					if a_type=='act_window':
						a_id = self.id_get(cr, 'ir.actions.%s'% a_type, a_action)
						cr.execute('select view_type,view_mode,name,view_id from ir_act_window where id=%d', (int(a_id),))
						action_type,action_mode,action_name,view_id = cr.fetchone()
						if view_id:
							cr.execute('SELECT type FROM ir_ui_view WHERE id=%d', (int(view_id),))
							action_mode, = cr.fetchone()
						cr.execute('SELECT view_mode FROM ir_act_window_view WHERE act_window_id=%d ORDER BY sequence LIMIT 1', (int(a_id),))
						if cr.rowcount:
							action_mode, = cr.fetchone()
						if action_type=='tree':
							values['icon'] = 'STOCK_INDENT'
						elif action_mode and action_mode.startswith('tree'):
							values['icon'] = 'STOCK_JUSTIFY_FILL'
						elif action_mode and action_mode.startswith('graph'):
							values['icon'] = 'terp-account'
						if not values['name']:
							values['name'] = action_name
				if rec.hasAttribute('sequence'):
					values['sequence'] = int(rec.getAttribute('sequence'))
				if rec.hasAttribute('icon'):
					values['icon'] = str(rec.getAttribute('icon'))
				if rec.hasAttribute('groups'):
					g_names = rec.getAttribute('groups').split(',')
					g_ids = []
					for group in g_names:
						g_ids.extend(self.pool.get('res.groups').search(cr, self.uid, [('name', '=', group)]))
					values['groups_id'] = [(6, 0, g_ids)]
				xml_id = rec.getAttribute('id').encode('utf8')
				self._test_xml_id(xml_id)
				pid = self.pool.get('ir.model.data')._update(cr, self.uid, 'ir.ui.menu', self.module, values, xml_id, idx==len(m_l)-1, mode=self.mode, res_id=res and res[0] or False)
			elif res:
				# the menuitem already exists
				pid = res[0]
				xml_id = idx==len(m_l)-1 and rec.getAttribute('id').encode('utf8')
				try:
					npid = self.pool.get('ir.model.data')._update_dummy(cr, self.uid, 'ir.ui.menu', self.module, xml_id, idx==len(m_l)-1)
				except:
					print 'Menu Error', self.module, xml_id, idx==len(m_l)-1
			else:
				# the menuitem does't exist but we are in branch (not a leaf)
				pid = self.pool.get('ir.ui.menu').create(cr, self.uid, {'parent_id' : pid, 'name' : menu_elem})
		if rec_id and pid:
			self.idref[rec_id] = pid

		if rec.hasAttribute('action') and pid:
			a_action = rec.getAttribute('action').encode('utf8')
			a_type = rec.getAttribute('type').encode('utf8') or 'act_window'
			a_id = self.id_get(cr, 'ir.actions.%s' % a_type, a_action)
			action = "ir.actions.%s,%d" % (a_type, a_id)
			self.pool.get('ir.model.data').ir_set(cr, self.uid, 'action', 'tree_but_open', 'Menuitem', [('ir.ui.menu', int(pid))], action, True, True, xml_id=rec_id)
		return ('ir.ui.menu', pid)

	def _tag_assert(self, cr, rec, data_node=None):
		rec_model = rec.getAttribute("model").encode('ascii')
		model = self.pool.get(rec_model)
		assert model, "The model %s does not exist !" % (rec_model,)
		rec_id = rec.getAttribute("id").encode('ascii')
		self._test_xml_id(rec_id)
		id = self.id_get(cr, False, rec_id)
		if data_node.getAttribute('noupdate') and not self.mode == 'init':
			for test in [i for i in rec.childNodes if (i.nodeType == i.ELEMENT_NODE and i.nodeName=="test")]:
				f_expr = test.getAttribute("expr").encode('utf-8')
				class d(dict):
					def __getitem__(self2, key):
						return getattr(model.browse(cr, self.uid, id), key)
				print "RESULT", eval(f_expr, d())

	def _tag_record(self, cr, rec, data_node=None):
		rec_model = rec.getAttribute("model").encode('ascii')
		model = self.pool.get(rec_model)
		assert model, "The model %s does not exist !" % (rec_model,)
		rec_id = rec.getAttribute("id").encode('ascii')
		self._test_xml_id(rec_id)

#		if not rec_id and not data_node.getAttribute('noupdate'):
#			print "Warning", rec_model

		if data_node.getAttribute('noupdate') and not self.mode == 'init':
			# check if the xml record has an id string
			if rec_id:
				id = self.pool.get('ir.model.data')._update_dummy(cr, self.uid, rec_model, self.module, rec_id)
				# check if the resource already existed at the last update
				if id:
					# if it existed, we don't update the data, but we need to 
					# know the id of the existing record anyway
					self.idref[rec_id] = id
					return None
				else:
					# if the resource didn't exist
					if rec.getAttribute("forcecreate"):
						# we want to create it, so we let the normal "update" behavior happen
						pass
					else:
						# otherwise do nothing
						return None
			else:
				# otherwise it is skipped
				return None
				
		res = {}
		for field in [i for i in rec.childNodes if (i.nodeType == i.ELEMENT_NODE and i.nodeName=="field")]:
#TODO: most of this code is duplicated above (in _eval_xml)...
			f_name = field.getAttribute("name").encode('utf-8')
			f_ref = field.getAttribute("ref").encode('ascii')
			f_search = field.getAttribute("search").encode('utf-8')
			f_model = field.getAttribute("model").encode('ascii')
			if not f_model and model._columns.get(f_name,False):
				f_model = model._columns[f_name]._obj
			f_use = field.getAttribute("use").encode('ascii') or 'id'
			f_val = False

			if len(f_search):
				q = eval(f_search, self.idref)
				field = []
				assert f_model, 'Define an attribute model="..." in your .XML file !'
				f_obj = self.pool.get(f_model)
				# browse the objects searched
				s = f_obj.browse(cr, self.uid, f_obj.search(cr, self.uid, q))
				# column definitions of the "local" object
				_cols = self.pool.get(rec_model)._columns
				# if the current field is many2many
				if (f_name in _cols) and _cols[f_name]._type=='many2many':
					f_val = [(6, 0, map(lambda x: x[f_use], s))]
				elif len(s):
					# otherwise (we are probably in a many2one field),
					# take the first element of the search
					f_val = s[0][f_use]
			elif len(f_ref):
				if f_ref=="null":
					f_val = False
				else:
					f_val = self.id_get(cr, f_model, f_ref)
			else:
				f_val = _eval_xml(self,field, self.pool, cr, self.uid, self.idref)
				if model._columns.has_key(f_name):
					if isinstance(model._columns[f_name], osv.fields.integer):
						f_val = int(f_val)
			res[f_name] = f_val
		id = self.pool.get('ir.model.data')._update(cr, self.uid, rec_model, self.module, res, rec_id or False, not data_node.getAttribute('noupdate'), noupdate=data_node.getAttribute('noupdate'), mode=self.mode )
		if rec_id:
			self.idref[rec_id] = id
		return rec_model, id

	def id_get(self, cr, model, id_str):
		if id_str in self.idref:
			return self.idref[id_str]
		mod = self.module
		if '.' in id_str:
			mod,id_str = id_str.split('.')
		result = self.pool.get('ir.model.data')._get_id(cr, self.uid, mod, id_str)
		return self.pool.get('ir.model.data').read(cr, self.uid, [result], ['res_id'])[0]['res_id']

	def parse(self, xmlstr):
		d = xml.dom.minidom.parseString(xmlstr)
		de = d.documentElement
		for n in [i for i in de.childNodes if (i.nodeType == i.ELEMENT_NODE and i.nodeName=="data")]:
			for rec in n.childNodes:
				if rec.nodeType == rec.ELEMENT_NODE:
					if rec.nodeName in self._tags:
						try:
							self._tags[rec.nodeName](self.cr, rec, n)
						except:
							self.logger.notifyChannel("init", netsvc.LOG_INFO, '\n'+rec.toxml())
							self.cr.rollback()
							raise
		self.cr.commit()
		return True

	def __init__(self, cr, module, idref, mode):
		self.logger = netsvc.Logger()
		self.mode = mode
		self.module = module
		self.cr = cr
		self.idref = idref
		self.pool = pooler.get_pool(cr.dbname)
#		self.pool = osv.osv.FakePool(module)
		self.uid = 1
		self._tags = {
			'menuitem': self._tag_menuitem,
			'record': self._tag_record,
			'assert': self._tag_assert,
			'report': self._tag_report,
			'wizard': self._tag_wizard,
			'delete': self._tag_delete,
			'ir_set': self._tag_ir_set,
			'function': self._tag_function,
			'workflow': self._tag_workflow,
			'act_window': self._tag_act_window,
		}

#
# Import a CSV file:
#     quote: "
#     delimiter: ,
#     encoding: UTF8
#
def convert_csv_import(cr, module, fname, csvcontent, idref={}, mode='init', noupdate=False):
	model = ('.'.join(fname.split('.')[:-1]).split('-'))[0]
	#remove folder path from model
	head, model = os.path.split(model)

	pool = pooler.get_pool(cr.dbname)

	input=StringIO.StringIO(csvcontent)
	reader = csv.reader(input, quotechar='"', delimiter=',')
	fields = reader.next()
	
	if not (mode == 'init' or 'id' in fields):
		return
	
	uid = 1
	datas = []
	for line in reader:
		datas.append( map(lambda x:x.decode('utf8').encode('utf8'), line))
		if len(datas) > COMMIT_STEP:
			pool.get(model).import_data(cr, uid, fields, datas,mode, module,noupdate)
			cr.commit()
			datas=[]

	if datas:
		pool.get(model).import_data(cr, uid, fields, datas,mode, module,noupdate)
		cr.commit()

#
# xml import/export
#
def convert_xml_import(cr, module, xmlstr, idref={}, mode='init'):
	obj = xml_import(cr, module, idref, mode)
	obj.parse(xmlstr)
	del obj
	return True

def convert_xml_export(res):
	uid=1
	pool=pooler.get_pool(cr.dbname)
	cr=pooler.db.cursor()
	idref = {}
	d = xml.dom.minidom.getDOMImplementation().createDocument(None, "terp", None)
	de = d.documentElement
	data=d.createElement("data")
	de.appendChild(data)
	de.appendChild(d.createTextNode('Some textual content.'))
	cr.commit()
	cr.close()

