from base.controllers.main import View
import openerpweb

class Export(View):
    _cp_path = "/base_export/export"

    def fields_get(self, req, model):
        Model = req.session.model(model)
        fields = Model.fields_get(False, req.session.eval_context(req.context))
        fields.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})
        return fields

    @openerpweb.jsonrequest
    def get_fields(self, req, model, prefix='', field_parent=None, name= ''):
        fields = self.fields_get(req, model)

        records = []
        for key, value in fields.items():
            record = {}

            id = prefix + (prefix and '/'or '') + key
            nm = name + (name and '/' or '') + value['string']
            record.update(id=id, string= nm, action='javascript: void(0)',
                          target=None, icon=None, children=[])
            records.append(record)

            if value.get('relation', False):
                ref = value.pop('relation')
                cfields = self.fields_get(req, ref)
                if (value['type'] == 'many2many'):
                    record['children'] = []
                    record['params'] = {'model': ref, 'prefix': id, 'name': nm}

                elif (value['type'] == 'many2one') or (value['type'] == 'many2many'):
                    cfields_order = cfields.keys()
                    cfields_order.sort(lambda x,y: -cmp(cfields[x].get('string', ''), cfields[y].get('string', '')))
                    children = []
                    for j, fld in enumerate(cfields_order):
                        cid = id + '/' + fld
                        cid = cid.replace(' ', '_')
                        children.append(cid)
                    record['children'] = children or []
                    record['params'] = {'model': ref, 'prefix': id, 'name': nm}

                else:
                    cfields_order = cfields.keys()
                    cfields_order.sort(lambda x,y: -cmp(cfields[x].get('string', ''), cfields[y].get('string', '')))
                    children = []
                    for j, fld in enumerate(cfields_order):
                        cid = id + '/' + fld
                        cid = cid.replace(' ', '_')
                        children.append(cid)
                    record['children'] = children or []
                    record['params'] = {'model': ref, 'prefix': id, 'name': nm}

        records.reverse()
        return records

    @openerpweb.jsonrequest
    def save_export_lists(self, req, name, model, field_list):
        result = {'resource':model, 'name':name, 'export_fields': []}
        for field in field_list:
            result['export_fields'].append((0, 0, {'name': field}))
        return req.session.model("ir.exports").create(result, req.session.eval_context(req.context))

    @openerpweb.jsonrequest
    def exist_export_lists(self, req, model):
        export_model = req.session.model("ir.exports")
        return export_model.read(export_model.search([('resource', '=', model)]), ['name'])

    @openerpweb.jsonrequest
    def delete_export(self, req, export_id):
        req.session.model("ir.exports").unlink(export_id, req.session.eval_context(req.context))
        return True

    @openerpweb.jsonrequest
    def namelist(self,req,  model, export_id):

        result = self.get_data(req, model, req.session.eval_context(req.context))
        ir_export_obj = req.session.model("ir.exports")
        ir_export_line_obj = req.session.model("ir.exports.line")

        field = ir_export_obj.read(export_id)
        fields = ir_export_line_obj.read(field['export_fields'])

        name_list = {}
        [name_list.update({field['name']: result.get(field['name'])}) for field in fields]
        print ":name_list::\n\n\n\n\n:",name_list
        return name_list

    def get_data(self, req, model, context=None):

        ids = []
        context = context or {}
        fields_data = {}
        proxy = req.session.model(model)
        fields = self.fields_get(req, model)
        if not ids:
            f1 = proxy.fields_view_get(False, 'tree', context)['fields']
            f2 = proxy.fields_view_get(False, 'form', context)['fields']

            fields = dict(f1)
            fields.update(f2)

        def rec(fields):
            _fields = {'id': 'ID' , '.id': 'Database ID' }
            def model_populate(fields, prefix_node='', prefix=None, prefix_value='', level=2):
                fields_order = fields.keys()
                fields_order.sort(lambda x,y: -cmp(fields[x].get('string', ''), fields[y].get('string', '')))

                for field in fields_order:
                    fields_data[prefix_node+field] = fields[field]
                    if prefix_node:
                        fields_data[prefix_node + field]['string'] = '%s%s' % (prefix_value, fields_data[prefix_node + field]['string'])
                    st_name = fields[field]['string'] or field
                    _fields[prefix_node+field] = st_name
                    if fields[field].get('relation', False) and level>0:
                        fields2 = self.fields_get(req,  fields[field]['relation'])
                        model_populate(fields2, prefix_node+field+'/', None, st_name+'/', level-1)
            model_populate(fields)

            return _fields

        return rec(fields)

