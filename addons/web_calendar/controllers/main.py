import base.common as openerpweb

from base.controllers.main import View

class CalendarView(View):
    _cp_path = "/base_calendar/calendarview"
    
    @openerpweb.jsonrequest
    def load(self, req, model, view_id, toolbar=False):
        fields_view = self.fields_view_get(req, model, view_id, 'calendar', toolbar=toolbar)
        return {'fields_view': fields_view}
