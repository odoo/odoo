##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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


# ON peut choisir lors de la definititon
# d'un skill de lui associer des skills
# de substitution et d'y associer des poids
# (et donc plus d'arbre ..)

from osv import osv, fields

# Wheight Category
# eg: years, in english, ..
class hr_skill_weight_category(osv.osv):
	_name ='hr_skill.weight.category'
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		}

hr_skill_weight_category()


# weight
# eg: 0 to 1, more than 5, good, bad
class hr_skill_weight(osv.osv):
	_name ='hr_skill.weight'
	_columns = {
		'name': fields.char('Name', size=64,required=True),
		'value': fields.float('Numerical value', required=True), 
		'category_id': fields.many2one('hr_skill.weight.category', 'Category', required=True, ondelete='cascade'),
		}# hr_skill.category ne passe pas (cad creation des tables) la premiere fois (hr_skill_category bien)

hr_skill_weight()


# Skill
# eg : Spanish, OO programming (-> skill) 
#      Langage, IT (->view)       
# Categories of weight
class hr_skill_skill(osv.osv):
	_name = 'hr_skill.skill'
	_columns = {
		'name': fields.char('Name', size=64,required=True), 
		'active': fields.boolean('Active'), 
		'weight': fields.float('Weight', required=True),
		'weight_category_id': fields.many2one('hr_skill.weight.category','Weight Category'),
		'parent_id': fields.many2one('hr_skill.skill', 'Parent', ondelete='cascade'),
		'child_ids': fields.one2many('hr_skill.skill', 'parent_id', 'Childs'),
		'view': fields.selection([('view','View'), ('skill','Skill')], 'Skill', required=True),
	}
	_defaults = {
		'view': lambda self,cr,uid,context: 'view',
		'weight': lambda self,cr,uid,context: 0,
		'active': lambda self,cr,uid,context: 1
	}
hr_skill_skill()



# Experience category
# eg : a degree or a professional experience
class hr_skill_experience_category(osv.osv):
	_name ='hr_skill.experience.category'
	_columns = {
		'name': fields.char('Name', size=64,required=True),
 	}
hr_skill_experience_category()


# Experience
# eg : a specific former job position or studies  
# each experience is associated with several couple skill - weight 
class hr_skill_experience(osv.osv):
	_name ='hr_skill.experience'
	_columns = {
		'name': fields.char('Name', size=64,required=True),
 		'skill_ids': fields.one2many('hr_skill.experience.skill','experience_id','Skills'),
  		'sequence': fields.integer('Sequence'),
  		'category_id' : fields.many2one('hr_skill.experience.category', 'Category'),
 	}
hr_skill_experience()


# Evaluation Category
class hr_skill_evaluation_category(osv.osv):
	_name ='hr_skill.evaluation.category'
	_columns = {
		'name': fields.char('Name', size=64,required=True),
 	}
hr_skill_evaluation_category()

# Evaluation
class hr_skill_evaluation(osv.osv):
	_name ='hr_skill.evaluation'
	_columns = {
		'name': fields.char('Evaluation name', size=64,required=True),
		'date': fields.date('Date',required=True),
		'interviewer_name': fields.char('Evaluator', size=64,required=True),
		'interviewee_name': fields.char('Evaluated People', size=64,required=True),
		'employee_id': fields.many2one('hr.employee', 'Evaluated Employee'),
		'note': fields.text('Notes'),
		'reference': fields.char('Reference', size=64),
		'category_id': fields.many2one('hr_skill.evaluation.category', 'Category', change_default=True),
		'experience_ids': fields.one2many('hr_skill.evaluation.experience','evaluation_id','Experience'),
 		'skill_ids': fields.one2many('hr_skill.evaluation.skill','evaluation_id','Skill'),

 	}
	def onchange_employee_id(self, cr, uid, ids, employee_id):
		if not employee_id:
			return {}
		empl = self.pool.get('hr.employee').browse(cr, uid, employee_id)
		return {'value': {'interviewee_name':empl.name} }
	
hr_skill_evaluation()

# Profile
# eg : management, web-dev.
# each profile is associated with several couple skill - weight
class hr_skill_profile(osv.osv):
	_name ='hr_skill.profile'
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'skill_ids': fields.one2many('hr_skill.profile.skill','profile_id','Skills'),
	}
hr_skill_profile()


# Position
# eg : Senior web-dev, junior logistician
# a position is associated to one (or several) profile
class hr_skill_position(osv.osv):
	_name ='hr_skill.position'
	_columns = {
		'name': fields.char('Name', size=64, required=True), 
		'employee_id': fields.many2one('hr.employee', 'Assigned Employee'),# ?? pq un many2one ?
		'profile_ids': fields.one2many('hr_skill.position.profile', 'position_id', 'Profiles'),
		'status': fields.selection([('open','Open'), ('assigned','Assigned'), ('unused','Unused')], 'Status'),
	}
hr_skill_position()



# definitition des relations :
class hr_skill_position_profile(osv.osv):
	_name ='hr_skill.position.profile'
	_columns = {
		'name': fields.char('Name', size=64),
		'weight_id': fields.many2one('hr_skill.weight','Weight',required=True),
		'position_id': fields.many2one('hr_skill.position','Position', ondelete='cascade',required=True),
		'profile_id': fields.many2one('hr_skill.profile','Profile', ondelete='cascade',required=True) ,
	}
	def onchange_profile_id(self, cr, uid, ids, profile_id):
		if not profile_id:
			return {}
		prof = self.pool.get('hr_skill.profile').browse(cr, uid, profile_id)
		return {'value': {'name':prof.name} }
hr_skill_position_profile()


class hr_skill_experience_skill(osv.osv):
	_name ='hr_skill.experience.skill'
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'weight_id': fields.many2one('hr_skill.weight','Weight', required=True),
		'skill_id': fields.many2one('hr_skill.skill','Skill', ondelete='cascade',required=True),
		'experience_id': fields.many2one('hr_skill.experience','Experience', ondelete='cascade',required=True) ,
	}
	def onchange_skill_id(self, cr, uid, ids, skill_id):
		if not skill_id:
			return {}
		sk = self.pool.get('hr_skill.skill').browse(cr, uid, skill_id)
		return {'value': {'name':sk.name} }
	
hr_skill_experience_skill()



class hr_skill_profile_skill(osv.osv):
	_name ='hr_skill.profile.skill'
	_columns = {
		'name': fields.char('Name', size=64),
		'weight_id': fields.many2one('hr_skill.weight','Weight',required=True),
		'profile_id': fields.many2one('hr_skill.profile','Profile', ondelete='cascade',required=True),
		'skill_id': fields.many2one('hr_skill.skill','Skill', ondelete='cascade',required=True, domain=[('view','<>','view')]),
	}
	
	def onchange_skill_id(self, cr, uid, ids, skill_id):
		if not skill_id:
			return {}
		sk = self.pool.get('hr_skill.skill').browse(cr, uid, skill_id)
		return {'value': {'name':sk.name} }
	
hr_skill_profile_skill()



class hr_skill_position_profile(osv.osv):
	_name ='hr_skill.position.profile'
	_columns = {
		'name': fields.char('Name', size=64),
		'weight_id': fields.many2one('hr_skill.weight','Weight',required=True, ondelete='cascade'),
		'position_id': fields.many2one('hr_skill.position','Position', ondelete='cascade',required=True),
		'profile_id': fields.many2one('hr_skill.profile','Profile', ondelete='cascade',required=True),
	}
hr_skill_profile_skill()



class hr_skill_evaluation_experience(osv.osv):
	_name ='hr_skill.evaluation.experience'
	_columns = {
		'name': fields.char('Name', size=64,required=True),
		'weight_id': fields.many2one('hr_skill.weight','Weight',required=True),
		'evaluation_id': fields.many2one('hr_skill.evaluation','Evaluation', ondelete='cascade', required=True),
		'experience_id': fields.many2one('hr_skill.experience','Experience', ondelete='cascade', required=True),
	}
	
	def onchange_experience_id(self, cr, uid, ids, experience_id): 
 		if not experience_id:
 			return {}
 		exp = self.pool.get('hr_skill.experience').browse(cr, uid, experience_id)
 		return {'value': {'name':exp.name} }

hr_skill_evaluation_experience()



class hr_skill_evaluation_skill(osv.osv):
	_name ='hr_skill.evaluation.skill'
	_columns = {
		'name': fields.char('Name', size=64),
		'weight_id': fields.many2one('hr_skill.weight','Weight',required=True),
		'evaluation_id': fields.many2one('hr_skill.evaluation','Evaluation', ondelete='cascade', required=True),
		'skill_id': fields.many2one('hr_skill.skill','Skill', ondelete='cascade', required=True),
	}
	def onchange_skill_id(self, cr, uid, ids, skill_id): 
 		if not skill_id:
 			return {}
 		sk = self.pool.get('hr_skill.skill').browse(cr, uid, skill_id)
 		return {'value': {'name':sk.name} }

hr_skill_evaluation_skill()

