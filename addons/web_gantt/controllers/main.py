import web.common as openerpweb
from web.controllers.main import View

class GanttView(View):
    _cp_path = "/web_gantt/ganttview"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        fields_view = self.fields_view_get(req, model, view_id, 'gantt')
        return {'fields_view':fields_view}

