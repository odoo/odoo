import openerpweb
from base.controllers.main import View

class GanttView(View):
    _cp_path = "/base_gantt/ganttview"
   
    model = ''
    domain = []
    context = {}
 
    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        fields_view = self.fields_view_get(req, model, view_id, 'gantt')
        return {'fields_view':fields_view}
        
    @openerpweb.jsonrequest
    def reload_gantt(self, req, **kw):
        
        model = req.session.model(kw['model'])
        domain = kw['domain']
        
        event_ids = model.search(domain)
        return event_ids
    