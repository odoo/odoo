import pickle
import osv
import pooler

def ir_set(cr, uid, key, key2, name, models, value, replace=True, isobject=False, meta=None):
	obj = pooler.get_pool(cr.dbname).get('ir.values')
	return obj.set(cr, uid, key, key2, name, models, value, replace, isobject, meta)

def ir_del(cr, uid, id):
	obj = pooler.get_pool(cr.dbname).get('ir.values')
	return obj.unlink(cr, uid, [id])

def ir_get(cr, uid, key, key2, models, meta=False, context={}, res_id_req=False):
	obj = pooler.get_pool(cr.dbname).get('ir.values')
	res = obj.get(cr, uid, key, key2, models, meta=meta, context=context, res_id_req=res_id_req)
	return res
