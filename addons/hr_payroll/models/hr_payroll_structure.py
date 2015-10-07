#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import fields, osv
from openerp.tools.translate import _


class hr_payroll_structure(osv.osv):
    """
    Salary structure used to defined
    - Basic
    - Allowances
    - Deductions
    """

    _name = 'hr.payroll.structure'
    _description = 'Salary Structure'
    _columns = {
        'name':fields.char('Name', required=True),
        'code':fields.char('Reference', size=64, required=True),
        'company_id':fields.many2one('res.company', 'Company', required=True, copy=False),
        'note': fields.text('Description'),
        'parent_id':fields.many2one('hr.payroll.structure', 'Parent'),
        'children_ids':fields.one2many('hr.payroll.structure', 'parent_id', 'Children', copy=True),
        'rule_ids':fields.many2many('hr.salary.rule', 'hr_structure_salary_rule_rel', 'struct_id', 'rule_id', 'Salary Rules'),
    }

    def _get_parent(self, cr, uid, context=None):
        obj_model = self.pool.get('ir.model.data')
        res = False
        data_id = obj_model.search(cr, uid, [('model', '=', 'hr.payroll.structure'), ('name', '=', 'structure_base')])
        if data_id:
            res = obj_model.browse(cr, uid, data_id[0], context=context).res_id
        return res

    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'parent_id': _get_parent,
    }

    _constraints = [
        (osv.osv._check_recursion, 'Error ! You cannot create a recursive Salary Structure.', ['parent_id']) 
    ]
        
    def copy(self, cr, uid, id, default=None, context=None):
        default = dict(default or {},
                       code=_("%s (copy)") % (self.browse(cr, uid, id, context=context).code))
        return super(hr_payroll_structure, self).copy(cr, uid, id, default, context=context)

    @api.cr_uid_ids_context
    def get_all_rules(self, cr, uid, structure_ids, context=None):
        """
        @param structure_ids: list of structure
        @return: returns a list of tuple (id, sequence) of rules that are maybe to apply
        """

        all_rules = []
        for struct in self.browse(cr, uid, structure_ids, context=context):
            all_rules += self.pool.get('hr.salary.rule')._recursive_search_of_rules(cr, uid, struct.rule_ids, context=context)
        return all_rules

    @api.cr_uid_ids_context
    def _get_parent_structure(self, cr, uid, struct_ids, context=None):
        if not struct_ids:
            return []
        parent = []
        for struct in self.browse(cr, uid, struct_ids, context=context):
            if struct.parent_id:
                parent.append(struct.parent_id.id)
        if parent:
            parent = self._get_parent_structure(cr, uid, parent, context)
        return parent + struct_ids
