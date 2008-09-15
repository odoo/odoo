# -*- encoding: utf-8 -*-
import time
import tools
from osv import fields,osv,orm
import os
import mx.DateTime
import base64

#AVAILABLE_STATES = [
#    ('draft','Unreviewed'),
#    ('open','Open'),
#    ('cancel', 'Refuse Bug'),
#    ('done', 'Done'),
#    ('pending','Pending')
#]
class crm_case_category2(osv.osv):
    _name = "crm.case.category2"
    _description = "Category2 of case"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Case Category2 Name', size=64, required=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
crm_case_category2()

class crm_case_stage(osv.osv):
    _name = "crm.case.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _columns = {
        'name': fields.char('Stage Name', size=64, required=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
crm_case_stage()

class crm_cases(osv.osv):
    _name = "crm.case"
    _inherit = "crm.case"
    _columns = {
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id)]"),
        'category2_id': fields.many2one('crm.case.category2','Category Name', domain="[('section_id','=',section_id)]"),
        'duration': fields.float('Duration'),
        'note': fields.text('Note'),
        'partner_name': fields.char('Employee Name', size=64),
        'partner_name2': fields.char('Employee Email', size=64),
        'partner_phone': fields.char('Phone', size=16),
        'partner_mobile': fields.char('Mobile', size=16),
    }

crm_cases()

class crm_menu_config_wizard(osv.osv_memory):
    
    _name='crm.menu.config_wizard'
    _columns = {
        'name':fields.char('Name', size=64),
        'meeting' : fields.boolean('Calendar of Meetings'),
        'lead' : fields.boolean('Leads'),
        'opportunity' : fields.boolean('Business Opportunities'),
        'jobs' : fields.boolean('Jobs Hiring Process'),
        'bugs' : fields.boolean('Bug Tracking'),
        'fund' : fields.boolean('Fund Raising Operations'),
    }
    
    def action_create(self, cr, uid, ids, *args):
        for res in self.read(cr,uid,ids):
            res.__delitem__('id')
    #        'update'
            for section in res :
                if res[section]:
                    file_name = 'crm_'+section+'_demo.xml'
                    try:
                        tools.convert_xml_import(cr, 'crm_configuration', tools.file_open(os.path.join('crm_configuration',file_name )),  {}, 'init', *args)
                    except Exception, e:
                        raise osv.except_osv('Error !', e)
                        
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.module.module.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }
    def action_cancel(self,cr,uid,ids,conect=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.module.module.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }
        
crm_menu_config_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

