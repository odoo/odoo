from base.controllers.main import View
import openerpweb
import StringIO
import csv
import xml.dom.minidom

def node_attributes(node):
    attrs = node.attributes

    if not attrs:
        return {}
    # localName can be a unicode string, we're using attribute names as
    # **kwargs keys and python-level kwargs don't take unicode keys kindly
    # (they blow up) so we need to ensure all keys are ``str``
    return dict([(str(attrs.item(i).localName), attrs.item(i).nodeValue)
                 for i in range(attrs.length)])

def _fields_get_all(req, model, views, context=None):

    if context is None:
        context = {}

    def parse(root, fields):
        for node in root.childNodes:
            if node.nodeName in ('form', 'notebook', 'page', 'group', 'tree', 'hpaned', 'vpaned'):
                parse(node, fields)
            elif node.nodeName=='field':
                attrs = node_attributes(node)
                name = attrs['name']
                fields[name].update(attrs)
        return fields

    def get_view_fields(view):
        return parse(
            xml.dom.minidom.parseString(view['arch'].encode('utf-8')).documentElement,
            view['fields'])

    model_obj = req.session.model(model)
    tree_view = model_obj.fields_view_get(views.get('tree', False), 'tree', context)
    form_view = model_obj.fields_view_get(views.get('form', False), 'form', context)
    fields = {}
    fields.update(get_view_fields(tree_view))
    fields.update(get_view_fields(form_view))
    return fields


class Export(View):
    _cp_path = "/base_export/export"

    def fields_get(self, req, model):
        Model = req.session.model(model)
        fields = Model.fields_get(False, req.session.eval_context(req.context))
        return fields

    @openerpweb.jsonrequest
    def get_fields(self, req, model, prefix='', name= '', field_parent=None, params={}):
        import_compat = params.get("import_compat", False)
        views_id = params.get("views_id", {})

        fields = _fields_get_all(req, model, views=views_id, context=req.session.eval_context(req.context))
        field_parent_type = params.get("parent_field_type",False)

        if import_compat and field_parent_type and field_parent_type == "many2one":
            fields = {}

        fields.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})
        records = []
        fields_order = fields.keys()
        fields_order.sort(lambda x,y: -cmp(fields[x].get('string', ''), fields[y].get('string', '')))

        for index, field in enumerate(fields_order):
            value = fields[field]
            record = {}
            if import_compat and value.get('readonly', False):
                ok = False
                for sl in value.get('states', {}).values():
                    for s in sl:
                        ok = ok or (s==['readonly',False])
                if not ok: continue

            id = prefix + (prefix and '/'or '') + field
            nm = name + (name and '/' or '') + value['string']
            record.update(id=id, string= nm, action='javascript: void(0)',
                          target=None, icon=None, children=[], field_type=value.get('type',False))
            records.append(record)

            if len(nm.split('/')) < 3 and value.get('relation', False):
                if import_compat:
                    ref = value.pop('relation')
                    cfields = self.fields_get(req, ref)
                    if (value['type'] == 'many2many'):
                        record['children'] = []
                        record['params'] = {'model': ref, 'prefix': id, 'name': nm}

                    elif value['type'] == 'many2one':
                        record['children'] = [id + '/id', id + '/.id']
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
                else:
                    ref = value.pop('relation')
                    cfields = self.fields_get(req, ref)
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
            fields.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})

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
                        fields2.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})
                        model_populate(fields2, prefix_node+field+'/', None, st_name+'/', level-1)
            model_populate(fields)
            return _fields
        return rec(fields)

    def export_csv(self, req, fields, result):
        fp = StringIO.StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        writer.writerow(fields)

        for data in result:
            row = []
            for d in data:
                if isinstance(d, basestring):
                    d = d.replace('\n',' ').replace('\t',' ')
                    try:
                        d = d.encode('utf-8')
                    except:
                        pass
                if d is False: d = None
                row.append(d)
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    @openerpweb.jsonrequest
    def export_data(self, req, model, fields, ids, domain, import_compat=False, context=None):
        context = req.session.eval_context(req.context)
        modle_obj = req.session.model(model)
        ids = ids or modle_obj.search(domain, context=context)

        field = fields.keys()
        result = modle_obj.export_data(ids, field , context).get('datas',[])

        if not import_compat:
            field = [val.strip() for val in fields.values()]
        return self.export_csv(req, field, result)
