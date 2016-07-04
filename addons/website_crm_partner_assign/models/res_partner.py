# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp.addons.website.models.website import slug


class res_partner_grade(osv.osv):
    _name = 'res.partner.grade'
    _inherit = ['res.partner.grade', 'website.published.mixin']

    _defaults = {
        'website_published': True,
    }

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = super(res_partner_grade, self)._website_url(cr, uid, ids, field_name, arg, context=context)
        for grade in self.browse(cr, uid, ids, context=context):
            res[grade.id] = "/partners/grade/%s" % (slug(grade))
        return res

class res_partner_grade(osv.osv):
    _order = 'sequence'
    _name = 'res.partner.grade'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'active': fields.boolean('Active'),
        'name': fields.char('Level Name'),
        'partner_weight': fields.integer('Level Weight',
            help="Gives the probability to assign a lead to this partner. (0 means no assignation.)"),
    }
    _defaults = {
        'active': lambda *args: 1,
        'partner_weight':1
    }

class res_partner_activation(osv.osv):
    _name = 'res.partner.activation'
    _order = 'sequence'

    _columns = {
        'sequence' : fields.integer('Sequence'),
        'name' : fields.char('Name', required=True),
    }


class res_partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
        'partner_weight': fields.integer('Level Weight',
            help="Gives the probability to assign a lead to this partner. (0 means no assignation.)"),
        'grade_id': fields.many2one('res.partner.grade', 'Level'),
        'activation' : fields.many2one('res.partner.activation', 'Activation', select=1),
        'date_partnership' : fields.date('Partnership Date'),
        'date_review' : fields.date('Latest Partner Review'),
        'date_review_next' : fields.date('Next Partner Review'),
        # customer implementation
        'assigned_partner_id': fields.many2one(
            'res.partner', 'Implemented by',
        ),
        'implemented_partner_ids': fields.one2many(
            'res.partner', 'assigned_partner_id',
            string='Implementation References',
        ),
    }
    _defaults = {
        'partner_weight': lambda *args: 0
    }
    
    def onchange_grade_id(self, cr, uid, ids, grade_id, context=None):
        res = {'value' :{'partner_weight':0}}
        if grade_id:
            partner_grade = self.pool.get('res.partner.grade').browse(cr, uid, grade_id)
            res['value']['partner_weight'] = partner_grade.partner_weight
        return res
