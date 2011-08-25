from base.controllers.main import View
import openerpweb

class DiagramView(View):
    _cp_path = "/base_diagram/diagram"

    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        fields_view = self.fields_view_get(req, model, view_id, 'diagram')
        return {'fields_view': fields_view}
    
    @openerpweb.jsonrequest
    def get_activity(self, req, id, name, kind, active_model, model):
        
        activity_id = req.session.model(model).search([('name','=',name),('kind','=',kind),('wkf_id','=',active_model)], 0, 0, 0, req.session.context)
        ids = req.session.model(model).search([], 0, 0, 0, req.session.context)
        return {'activity_id':activity_id, 'ids': ids}
    
    @openerpweb.jsonrequest
    def get_diagram_info(self, req, **kw):
        id = kw['id']
        model = kw['model']
        node = kw['node']
        connector = kw['connector']
        src_node = kw['src_node']
        des_node = kw['des_node']
        visible_node_fields = kw.get('visible_node_fields',[])
        invisible_node_fields = kw.get('invisible_node_fields',[])
        node_fields_string = kw.get('node_fields_string',[])
        connector_fields = kw.get('connector_fields',[])
        connector_fields_string = kw.get('connector_fields_string',[])
        
        bgcolors = {}
        shapes = {}
        bgcolor = kw.get('bgcolor','')
        shape = kw.get('shape','')
        
        if bgcolor:
            for color_spec in bgcolor.split(';'):
                if color_spec:
                    colour, color_state = color_spec.split(':')
                    bgcolors[colour] = color_state
                    
        if shape:
            for shape_spec in shape.split(';'):
                if shape_spec:
                    shape_colour, shape_color_state = shape_spec.split(':')
                    shapes[shape_colour] = shape_color_state
                    
        ir_view = req.session.model('ir.ui.view')
        graphs = ir_view.graph_get(int(id), model, node, connector, src_node, des_node, False,
                          (140, 180), req.session.context)
        nodes = graphs['nodes']
        transitions = graphs['transitions']
        isolate_nodes = {}
        for blnk_node in graphs['blank_nodes']:
            isolate_nodes[blnk_node['id']] = blnk_node
        else:
            y = map(lambda t: t['y'],filter(lambda x: x['y'] if x['x']==20 else None, nodes.values()))
            y_max = (y and max(y)) or 120
        
        connectors = {}
        list_tr = []

        for tr in transitions:
            list_tr.append(tr)
            connectors.setdefault(tr, {
                'id': tr,
                's_id': transitions[tr][0],
                'd_id': transitions[tr][1]
            })
        connector_tr = req.session.model(connector)
        connector_ids = connector_tr.search([('id', 'in', list_tr)], 0, 0, 0, req.session.context)
        
        data_connectors =connector_tr.read(connector_ids, connector_fields, req.session.context)
        
        
        for tr in data_connectors:
            t = connectors.get(str(tr['id']))
            t.update({
                      'source': tr[src_node][1],
                      'destination': tr[des_node][1],
                      'options': {}
                      })

            for i, fld in enumerate(connector_fields):
                t['options'][connector_fields_string[i]] = tr[fld]
        
        fields = req.session.model('ir.model.fields')
        field_ids = fields.search([('model', '=', model), ('relation', '=', node)], 0, 0, 0, req.session.context)
        field_data = fields.read(field_ids, ['relation_field'], req.session.context)
        node_act = req.session.model(node)
        search_acts = node_act.search([(field_data[0]['relation_field'], '=', id)], 0, 0, 0, req.session.context)
        data_acts = node_act.read(search_acts, invisible_node_fields + visible_node_fields, req.session.context)
        
        for act in data_acts:
            n = nodes.get(str(act['id']))
            if not n:
                n = isolate_nodes.get(act['id'], {})
                y_max += 140
                n.update({'x': 20, 'y': y_max})
                nodes[act['id']] = n

            n.update(
                id=act['id'],
                color='white',
                shape='ellipse',
                options={}
            )
            for color, expr in bgcolors.items():
                if eval(expr, act):
                    n['color'] = color

            for shape, expr in shapes.items():
                if eval(expr, act):
                    n['shape'] = shape

            for i, fld in enumerate(visible_node_fields):
                n['options'][node_fields_string[i]] = act[fld]
                
        #to relate m2o field of transition to corresponding o2m in activity
        in_transition_field_id = fields.search([('relation', '=', connector), ('relation_field', '=', des_node), ('model', '=', node)], 0, 0, 0, req.session.context)
        in_transition_field = fields.read(in_transition_field_id[0], ['name'], req.session.context)['name']

        out_transition_field_id = fields.search([('relation', '=', connector), ('relation_field', '=', src_node), ('model', '=', node)], 0, 0, 0, req.session.context)
        out_transition_field = fields.read(out_transition_field_id[0], ['name'], req.session.context)['name']
        
        id_model = req.session.model(model).read([id],['name'], req.session.context)[0]['name']
        return dict(nodes=nodes, conn=connectors, in_transition_field=in_transition_field, out_transition_field=out_transition_field, id_model = id_model)
