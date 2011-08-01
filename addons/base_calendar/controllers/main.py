from base.controllers.main import View
import openerpweb

class CalendarView(View):
    _cp_path = "/base_calendar/calendarview"
    
    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        fields_view = self.fields_view_get(req, model, view_id, 'calendar')
        return {'fields_view': fields_view}
