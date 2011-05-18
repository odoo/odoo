from base.controllers.main import View, clean_action
import openerpweb

class Dashboard(View):
    _cp_path = "/base_dashboard/dashboard"
    
    @openerpweb.jsonrequest
    def load(self, req, node_attrs):
        
        action_id = int(node_attrs['name'])
        actions = req.session.model('ir.actions.actions')
        result = actions.read([action_id],['type'], req.session.context)
        if not result:
            raise _('Action not found!')
        action = req.session.model(result[0]['type']).read([action_id], False, req.session.context)[0]
        clean_action(action, req.session)
        return {'action': action}