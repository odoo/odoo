from base.controllers.main import View
import openerpweb

class Dashboard(View):
    _cp_path = "/base_dashboard/dashboard"
    
    @openerpweb.jsonrequest
    def load(self, req, node):
        return