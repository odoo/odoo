from osv import osv
from osv import fields

class postpone_wizard(osv.osv_memory):
    _name="postpone.wizard"
    def button_postpone(self, cr, uid, ids, context=None):
        log_obj=self.pool.get('project.scrum.product.backlog')
        if context is None:
            context = {}
        for product in log_obj.browse(cr, uid, ids, context=context):
            tasks_id = []
            for task in product.tasks_id:
                if task.state != 'done':
                    tasks_id.append(task.id)
            clone_id = log_obj.copy(cr, uid, product.id, {
                'name': 'PARTIAL:'+ product.name ,
                'sprint_id':False,
                'tasks_id':[(6, 0, tasks_id)],
                                })
        log_obj.write(cr, uid, ids, {'state':'cancel'}, context=context)
        return {}
postpone_wizard()