# -*- coding: utf-8 -*-
try:
    # embedded
    import openerp.addons.web.common.http as openerpweb
    from openerp.addons.web.controllers.main import View
except ImportError:
    # standalone
    import web.common.http as openerpweb
    from web.controllers.main import View

from lxml import etree

class GraphView(View):
    _cp_path = '/web_graph/graph'

    @openerpweb.jsonrequest
    def data_get(self, req, model=None, domain=[], context={}, group_by=[], view_id=False, orientation=False, stacked=False, mode="bar", **kwargs):
        obj = req.session.model(model)

        res = obj.fields_view_get(view_id, 'graph')
        fields = res['fields']
        toload = filter(lambda x: x not in fields, group_by)
        if toload:
            fields.update( obj.fields_get(toload, context) )

        tree = etree.fromstring(res['arch'])

        pos = 0
        xaxis = group_by or []
        yaxis = []
        for field in tree.iter(tag='field'):
            if (field.tag != 'field') or (not field.get('name')):
                continue
            assert field.get('name'), "This <field> tag must have a 'name' attribute."
            if (not group_by) and ((not pos) or field.get('group')):
                xaxis.append(field.get('name'))
            if pos and not field.get('group'):
                yaxis.append(field.get('name'))
            pos += 1

        assert len(xaxis), "No field for the X axis!"
        assert len(yaxis), "No field for the Y axis!"

        # Convert a field's data into a displayable string

        ticks = {}
        def _convert_key(field, data):
            if fields[field]['type']=='many2one':
                data = data and data[0]
            return data

        def _convert(field, data, tick=True):
            if fields[field]['type']=='many2one':
                data = data and data[1]
            elif (fields[field]['type']=='selection') and (type(fields[field]['selection']) in (list, tuple)):
                d = dict(fields[field]['selection'])
                data = d[data]
            if tick:
                return ticks.setdefault(data, len(ticks))
            return data or 0

        def _orientation(x, y):
            if not orientation:
                return (x,y)
            return (y,x)

        result = []
        if mode=="pie":
            res = obj.read_group(domain, yaxis+[xaxis[0]], [xaxis[0]], context=context)
            for record in res:
                result.append( {
                    'data': [(_convert(xaxis[0], record[xaxis[0]]), record[yaxis[0]])],
                    'label': _convert(xaxis[0], record[xaxis[0]], tick=False)
                })

        elif (not stacked) or (len(xaxis)<2):
            for x in xaxis:
                res = obj.read_group(domain, yaxis+[x], [x], context=context)
                result.append( {
                    'data': map(lambda record: _orientation(_convert(x, record[x]), record[yaxis[0]] or 0), res),
                    'label': fields[x]['string']
                })
        else:
            xaxis.reverse()
            axis = obj.read_group(domain, yaxis+xaxis[0:1], xaxis[0:1], context=context)
            for x in axis:
                key = x[xaxis[0]]
                res = obj.read_group(domain+[(xaxis[0],'=',_convert_key(xaxis[0], key))], yaxis+xaxis[1:2], xaxis[1:2], context=context)
                result.append( {
                    'data': map(lambda record: _orientation(_convert(xaxis[1], record[xaxis[1]]), record[yaxis[0]] or 0), res),
                    'label': _convert(xaxis[0], key, tick=False)
                })

        res = {
            'data': result,
            'ticks': map(lambda x: (x[1], x[0]), ticks.items())
        }
        return res

