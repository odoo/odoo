# -*- coding :utf-8 -*-

from osv import osv, fields
import time, pooler, copy

class audittrail_rule(osv.osv):
	_name = 'audittrail.rule'
	_columns = {
		"name": fields.char("Rule Name", size=32, required=True),
		"object_id": fields.many2one('ir.model', 'Object', required=True),
		"user_id": fields.many2many('res.users', 'audittail_rules_users', 'user_id', 'rule_id', 'Users'),
		"log_read": fields.boolean("Log reads"),
		"log_write": fields.boolean("Log writes"),
		"log_unlink": fields.boolean("Log deletes"),
		"log_create": fields.boolean("Log creates"),
		"state": fields.selection((("draft", "Draft"),("subscribed", "Subscribed")), "State", required=True)
	}
	_defaults = {
		'state': lambda *a: 'draft',
		'log_create': lambda *a: 1,
		'log_unlink': lambda *a: 1,
		'log_write': lambda *a: 1,
	}
	__functions = {}

	def subscribe(self, cr, uid, ids, *args):
		for thisrule in self.browse(cr, uid, ids):
			obj = self.pool.get(thisrule.object_id.model)
			if not obj:
				print ("%s WARNING:audittrail:%s is not part of the pool -- change audittrail depends -- setting rule: %s as DRAFT" % (time.strftime('%a, %d %b %Y %H:%M:%S'), thisrule.object_id.model, thisrule.name))
				self.write(cr, uid, ids, {"state": "draft"})
				return False
			for field in ('read','write','create','unlink'):
				if getattr(thisrule, 'log_'+field):
					# backup corresponding method
					self.__functions.setdefault(thisrule.id, [])
					self.__functions[thisrule.id].append( (obj, field, getattr(obj,field)) )
					uids_to_log = []
					for user in thisrule.user_id:
						uids_to_log.append(user.id)
					# override it with the logging variant
					setattr(obj, field, self.logging_fct(getattr(obj,field), thisrule.object_id, uids_to_log))
		self.write(cr, uid, ids, {"state": "subscribed"})
		return True

	def logging_fct(self, fct_src, object, logged_uids):
		if object.model=="audittrail.log":
			return fct_src
		def my_fct( cr, uid, *args, **args2):
			if not len(logged_uids) or uid in logged_uids:
				self.pool.get('audittrail.log').create(cr, uid, {"method": fct_src.__name__, "object_id": object.id, "user_id": uid, "args": "%s, %s" % (str(args), str(args2)), "name": "%s %s %s" % (fct_src.__name__, object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
			return fct_src( cr, uid, *args, **args2)
		return my_fct

	def unsubscribe(self, cr, uid, ids, *args):
		for thisrule in self.browse(cr, uid, ids):
			for function in self.__functions[thisrule.id]:
				setattr(function[0], function[1], function[2])
		self.write(cr, uid, ids, {"state": "draft"})
		return True

#	def __init__(self, *args):
#		super(audittrail_rule, self).__init__(*args)
#		cr = pooler.db.cursor()
#FIXME: ah merde, ca craint pour le multi-db! Une solution serait d'overrider d'office toutes les methodes
# et de checker dans la methode elle meme s'il faut logger ou pas, mais ca risque de tout faire ramer violemment
# une autre solution (bien meilleure, il me semble) est de rajouter une méthode "db_dependant_init" dans osv qui est overridable
# et appellée dans le __init__ de osv (comme creation des tables et chargement des données)
# a merde, ca marche pas, vu que plusieurs utilisateurs peuvent etre sur des bases differentes en meme temps
#		self.subscribe(cr, 1, self.search(cr, 1, [('state','=','subscribed')]))
#		cr.commit()
#		cr.close()
#		del cr

class audittrail_log(osv.osv):
	_name = 'audittrail.log'
	_columns = {
		"name": fields.char("Name", size=32),
		"object_id": fields.many2one('ir.model', 'Object'),
		"user_id": fields.many2one('res.users', 'User'),
		"method": fields.selection((('read', 'Read'), ('write', 'Write'), ('unlink', 'Delete'), ('create', 'Create')), "Method"),
		"args": fields.text("Arguments"),
		"timestamp": fields.datetime("Timestamp")
	}
	_defaults = {
		"timestamp": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S")
	}

audittrail_log()
audittrail_rule()


