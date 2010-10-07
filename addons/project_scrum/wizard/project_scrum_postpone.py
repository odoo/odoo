from osv import osv
from osv import fields

class postpone_wizard(osv.osv_memory):
    _name="postpone.wizard"
    def button_postpone(self, cr, uid, ids, context=None):
       self.pool.get('project.scrum.product.backlog').button_postpone(cr, uid, ids, context)
       return {}
postpone_wizard()