import openerp

class DiagramView(openerp.http.Controller):

    @openerp.http.route('/web_diagram/diagram/get_diagram_info', type='json', auth='user')
    def get_diagram_info(self, req, id, model, node, connector,
                         src_node, des_node, label, **kw):

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
        graphs = ir_view.graph_get(
            int(id), model, node, connector, src_node, des_node, label,
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
                'id': int(tr),
                's_id': transitions[tr][0],
                'd_id': transitions[tr][1]
            })
        connector_tr = req.session.model(connector)
        connector_ids = connector_tr.search([('id', 'in', list_tr)], 0, 0, 0, req.session.context)

        data_connectors =connector_tr.read(connector_ids, connector_fields, req.session.context)

        for tr in data_connectors:
            transition_id = str(tr['id'])
            _sourceid, label = graphs['label'][transition_id]
            t = connectors[transition_id]
            t.update(
                source=tr[src_node][1],
                destination=tr[des_node][1],
                options={},
                signal=label
            )

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
                n.update(x=20, y=y_max)
                nodes[act['id']] = n

            n.update(
                id=act['id'],
                color='white',
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

        _id, name = req.session.model(model).name_get([id], req.session.context)[0]
        return dict(nodes=nodes,
                    conn=connectors,
                    name=name,
                    parent_field=graphs['node_parent_field'])
