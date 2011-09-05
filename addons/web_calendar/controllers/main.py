import web.common as openerpweb

from web.controllers.main import View

class CalendarView(View):
    _cp_path = "/web_calendar/calendarview"
    
    @openerpweb.jsonrequest
    def load(self, req, model, view_id, toolbar=False):
        fields_view = self.fields_view_get(req, model, view_id, 'calendar', toolbar=toolbar)
        return {'fields_view': fields_view}
