import openerp
from openerp.http import request

class KanbanView(openerp.http.Controller):

    @openerp.http.route('/web_kanban/recompute_aggregates', type='json', auth='user')
    def recompute_aggregates(self, req, model, fields, group_fields, groups, **kw):
        result = {}
        Model = req.session.model(model)
        for group in groups:
            result[group.get('index')] = Model.read_group(group.get('domain'), fields, group_fields, context=request.context)
        return result