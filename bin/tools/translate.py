##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os
from os.path import join
import fnmatch
import csv, xml.dom, re
import osv, tools, pooler
import ir
import netsvc
from tools.misc import UpdateableStr

#
# TODO: a caching method
#
def translate(cr, uid, name, source_type, lang, source=None):
	if source and name:
		cr.execute('select value from ir_translation where lang=%s and type=%s and name=%s and src=%s', (lang, source_type, str(name), source))
	elif name:
		cr.execute('select value from ir_translation where lang=%s and type=%s and name=%s', (lang, source_type, str(name)))
	elif source:
		cr.execute('select value from ir_translation where lang=%s and type=%s and src=%s', (lang, source_type, source))
	res_trans = cr.fetchone()
	res = res_trans and res_trans[0] or False
	return res
	
def translate_code(cr, uid, source, context):
	lang = context.get('lang', False)
	if lang:
		return translate(cr, uid, None, 'code', lang, source)
	else:
		return source
		
_ = lambda source: translate_code(cr, uid, source, context)

# Methods to export the translation file

def trans_parse_xsl(de):
	res = []
	for n in [i for i in de.childNodes if (i.nodeType == i.ELEMENT_NODE)]:
		if n.hasAttribute("t"):
			for m in [j for j in n.childNodes if (j.nodeType == j.TEXT_NODE)]:
				l = m.data.strip().replace('\n',' ')
				if len(l):
					res.append(l.encode("utf8"))
		res.extend(trans_parse_xsl(n))
	return res

def trans_parse_rml(de):
	res = []
	for n in [i for i in de.childNodes if (i.nodeType == i.ELEMENT_NODE)]:
		for m in [j for j in n.childNodes if (j.nodeType == j.TEXT_NODE)]:
			string_list = [s.replace('\n', ' ').strip() for s in re.split('\[\[.+?\]\]', m.data)]
			for s in string_list:
				if s:
					res.append(s.encode("utf8"))
		res.extend(trans_parse_rml(n))
	return res

def trans_parse_view(de):
	res = []
	if de.hasAttribute("string"):
		s = de.getAttribute('string')
		if s:
			res.append(s.encode("utf8"))
	for n in [i for i in de.childNodes if (i.nodeType == i.ELEMENT_NODE)]:
		res.extend(trans_parse_view(n))
	return res

# tests whether an object is in a list of modules
def in_modules(object_name, modules):
	if 'all' in modules:
		return True
		
	module_dict = {
		'ir': 'base',
		'res': 'base',
		'workflow': 'base',
	}
	module = object_name.split('.')[0]
	module = module_dict.get(module, module)
	return module in modules

def trans_generate(lang, modules, dbname=None):
	if not dbname:
		dbname=tools.config['db_name']
	pool = pooler.get_pool(dbname)
	trans_obj = pool.get('ir.translation')
	cr = pooler.get_db(dbname).cursor()
	uid = 1
	l = pool.obj_pool.items()
	l.sort()
	out = [["type","name","res_id","src","value"]]

#TODO: do everything through to_translate, for that, we'll probably need to change its
#format and have records = list of tuples (id, name, source) instead of just source
	to_translate = []
	
	# object fields
	for obj_name, obj in l:
		if in_modules(obj_name, modules):
			for field_name, field_def in obj._columns.iteritems():
				name = obj_name + "," + field_name
				value = ""
				if lang:
					cr.execute("SELECT * FROM ir_translation WHERE type='field' AND name=%s AND lang=%s", (name,lang))
					res = cr.dictfetchall()
					if len(res):
						value = res[0]['value']
				out.append(["field", name, "0", field_def.string.encode('utf8'), value])
				if field_def.translate:
					ids = osv.orm.orm.search(obj, cr, uid, [])
					obj_values = obj.read(cr, uid, ids, [field_name])
					for obj_value in obj_values:
						trans = ""
						if lang:
							cr.execute("SELECT * FROM ir_translation WHERE type='model' AND name=%s AND res_id=%d AND lang=%s", (name, obj_value['id'], lang))
							res = cr.dictfetchall()
							if len(res):
								trans = res[0]['value']
						out.append(["model", name, obj_value['id'], obj_value[field_name], trans])
				if hasattr(field_def, 'selection') and isinstance(field_def.selection, (list, tuple)):
					for key, val in field_def.selection:
						to_translate.append(["selection", name, [val.encode('utf8')]])

	# reports (xsl and rml)
	obj = pool.get("ir.actions.report.xml")
	for i in obj.read(cr, uid, osv.orm.orm.search(obj, cr, uid, [])):
		if in_modules(i["model"], modules):
			name = i["report_name"]
			fname = ""
			if i["report_rml"]:
				fname = i["report_rml"]
				parse_func = trans_parse_rml
				report_type = "rml"
			elif i["report_xsl"]:
				fname = i["report_xsl"]
				parse_func = trans_parse_xsl
				report_type = "xsl"
			try:
				xmlstr = tools.file_open(fname).read()
				d = xml.dom.minidom.parseString(xmlstr)
				to_translate.append([report_type, name, parse_func(d.documentElement)])
			except IOError:
				if fname:
					print "Warning: couldn't export translation for report %s" % name, report_type, fname

	# views
	obj = pool.get("ir.ui.view")
	for i in obj.read(cr, uid, osv.orm.orm.search(obj, cr, uid, [])):
		if in_modules(i["model"], modules):
			d = xml.dom.minidom.parseString(i['arch'])
			to_translate.append(["view", i['model'], trans_parse_view(d.documentElement)])
	
	# wizards
	for service_name, obj in netsvc._service.iteritems():
		if service_name.startswith('wizard.'):
			for state_name, state_def in obj.states.iteritems():
				if 'result' in state_def:
					result = state_def['result']
					if result['type'] != 'form':
						continue

					name = obj.wiz_name + ',' + state_name

					# export fields
					for field_name, field_def in result['fields'].iteritems():
						if 'string' in field_def:
							source = field_def['string']
							res_name = name + ',' + field_name
							to_translate.append(["wizard_field", res_name, [source]])

					# export arch
					arch = result['arch']
					if not isinstance(arch, UpdateableStr):
						d = xml.dom.minidom.parseString(arch)
						to_translate.append(["wizard_view", name, trans_parse_view(d.documentElement)])

					# export button labels
					for but_args in result['state']:
						button_name = but_args[0]
						button_label = but_args[1]
						res_name = name + ',' + button_name
						to_translate.append(["wizard_button", res_name, [button_label]])
	
	# code
	for root, dirs, files in os.walk(tools.config['root_path']):
		for fname in fnmatch.filter(files, '*.py'):
			frelativepath = join(root, fname)
			code_string = tools.file_open(frelativepath, subdir='').read()
			
# TODO: add support for """ and '''... These should use the DOTALL flag
# DOTALL
#     Make the "." special character match any character at all, including a
#     newline; without this flag, "." will match anything except a newline.
			# *? is the non-greedy version of the * qualifier
			iter = re.finditer(
				'[^a-zA-Z0-9_]_\([\s]*["\'](.*?)["\'][\s]*\)',
				code_string)
			for i in iter:
				source = i.group(1).encode('utf8')
# TODO: check whether the same string has already been exported
				res = trans_obj._get_source(cr, uid, frelativepath, 'code', lang, source) or ''
				out.append(["code", frelativepath, "0", source, res])

	# translate strings marked as to be translated
	for type, name, sources in to_translate:
		for source in sources:
			trans = trans_obj._get_source(cr, uid, name, type, lang, source)
			out.append([type, name, "0", source, trans or ''])
			
	cr.close()
	return out

def trans_load(db_name, filename, lang, strict=False):
	logger = netsvc.Logger()
	data=''
	try:
		data=file(filename,'r').read().split('\n')
	except IOError:
		logger.notifyChannel("init", netsvc.LOG_ERROR, "couldn't read file")
	return trans_load_data(db_name, data, lang, strict=False)

def trans_load_data(db_name, data, lang, strict=False, lang_name=None):
	logger = netsvc.Logger()
	logger.notifyChannel("init", netsvc.LOG_INFO, 'loading translation file for language %s' % (lang))
	pool = pooler.get_pool(db_name)
	lang_obj = pool.get('res.lang')
	trans_obj = pool.get('ir.translation')
	try:
		uid = 1
		cr = pooler.get_db(db_name).cursor()

		ids = lang_obj.search(cr, uid, [('code','=',lang)])
		if not ids:
			if not lang_name:
				lang_name=lang
				languages=tools.get_languages()
				if lang in languages:
					lang_name=languages[lang]
			ids = lang_obj.create(cr, uid, {'code':lang, 'name':lang_name, 'translatable':1})
		else:
			lang_obj.write(cr, uid, ids, {'translatable':1})
		lang_ids = lang_obj.search(cr, uid, [])
		langs = lang_obj.read(cr, uid, lang_ids)
		ls = map(lambda x: (x['code'],x['name']), langs)

		ir.ir_set(cr, uid, 'meta', 'lang', 'lang', [('res.users',False,)], 'en', True, False, meta = {'type':'selection', 'string':'Language', 'selection':ls})

		ids = pool.get('res.users').search(cr, uid, [])
		for id in ids:
			ir.ir_set(cr, uid, 'meta', 'lang', 'lang', [('res.users',id,)], lang, True, False)

		reader = csv.reader(data)
		
		# read the first line of the file (it contains columns titles)
		for row in reader:
			f = row
			break

		# read the rest of the file
		line = 1
		for row in reader:
			line += 1
			try:
				# skip empty rows and rows where the translation field is empty
				if (not row) or (not row[4]):
					continue
					
				# dictionary which holds values for this line of the csv file
				# {'lang': ..., 'type': ..., 'name': ..., 'res_id': ..., 'src': ..., 'value': ...}
				dic = {'lang': lang}
				for i in range(len(f)):
					if trans_obj._columns[f[i]]._type=='integer':
						row[i] = row[i] and int(row[i]) or False
					dic[f[i]] = row[i]
					
				if dic['type'] == 'model' and not strict:
					(model, field) = dic['name'].split(',')

					# get the ids of the resources of this model which share
					# the same source
					obj = pool.get(model)
					if obj:
						ids = osv.orm.orm.search(obj, cr, uid, [(field, '=', dic['src'])])

						# if the resource id (res_id) is in that list, use it, otherwise use the whole list
						ids = (dic['res_id'] in ids) and [dic['res_id']] or ids
						for id in ids:
							dic['res_id'] = id
							ids = trans_obj.search(cr, uid, [
								('lang', '=', lang), 
								('type', '=', dic['type']), 
								('name', '=', dic['name']), 
								('src', '=', dic['src']),
								('res_id', '=', dic['res_id'])
							])
							if ids:
								trans_obj.write(cr, uid, ids, {'value': dic['value']})
							else:
								trans_obj.create(cr, uid, dic)
				else:
					ids = trans_obj.search(cr, uid, [
						('lang', '=', lang), 
						('type', '=', dic['type']), 
						('name', '=', dic['name']), 
						('src', '=', dic['src'])
					])
					if ids:
						trans_obj.write(cr, uid, ids, {'value': dic['value']})
					else:
						trans_obj.create(cr, uid, dic)
			except Exception, e:
				print 'Import error', e, 'on line %d: %s!' % (line, row)
		cr.commit()
		cr.close()
		logger.notifyChannel("init", netsvc.LOG_INFO, "translation file loaded succesfully")
	except IOError:
		logger.notifyChannel("init", netsvc.LOG_ERROR, "couldn't read file")

