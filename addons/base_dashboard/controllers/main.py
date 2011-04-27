from base.controllers.main import View
import openerpweb

class Dashboard(View):
    _cp_path = "/base_dashboard/dashboard"
    
    @openerpweb.jsonrequest
    def load(self, req, node_attrs):
        
        self.action_id = int(node_attrs['name'])
        actions = req.session.model('ir.actions.actions')
        result = actions.read([self.action_id],['type'], req.session.context)
        if not result:
            raise _('Action not found!')
        self.action = req.session.model(result[0]['type']).read([self.action_id], False, req.session.context)[0]
        
        return {'action': self.action}