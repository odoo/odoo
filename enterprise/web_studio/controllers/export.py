# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import binascii
import io
import zipfile
from collections import OrderedDict

from lxml import etree
from lxml.builder import E

from odoo import models
from odoo.http import request
from odoo.osv.expression import OR
from odoo.tools import topological_sort
from base64 import b64decode


# The fields whose value is some XML content
XML_FIELDS = [('ir.ui.view', 'arch')]


def generate_archive(module, export_info):
    """ Returns a zip file containing the given module with the given data.
        Returns:
            bytes: A byte string containing the zip file.
    """
    with io.BytesIO() as f:
        with zipfile.ZipFile(f, 'w') as archive:
            for filename, content in generate_module(module, export_info):
                archive.writestr(module.name + '/' + filename, content)
        return f.getvalue()


def generate_module(module, export_info):
    """ Return an iterator of pairs (filename, content) to put in the exported
        module. Returned filenames are local to the module directory.
        Groups exported data by model in separated files.
        The content of the files is yielded as an encoded bytestring (utf-8)
        Yields:
            tuple: A tuple containing the filename and content.
    """
    has_website = _has_website()
    # Generate xml files and yield them
    filenames = []          # filenames to include in the module to export
    # depends contains module dependencies of the module to export, as a result
    # we add web_studio by default to deter importing studio customizations
    # in community databases
    depends = {'web_studio'}
    skipped_fields = []            # non-exported field values

    # Generate xml files for the data to export
    data, export, circular_dependencies = export_info
    model_data_getter = ir_model_data_getter(data)
    for model, filepath, records, fields, no_update in export:
        (xml, binary_files, new_dependencies, skipped) = _serialize_model(module, model, records, fields, no_update, has_website, model_data_getter)
        if xml is not None:
            yield from binary_files
            yield (filepath, xml)
            filenames.append(filepath)
            depends.update(new_dependencies)
        skipped_fields.extend(skipped)

    # SPECIFIC: Confirm demo sale orders
    if 'demo/sale_order.xml' in filenames:
        filepath = 'demo/sale_order_confirm.xml'
        sale_orders_data = data.filtered(lambda d: d.model == "sale.order")
        sale_orders = request.env["sale.order"].browse(sale_orders_data.mapped("res_id"))
        xmlids = [model_data_getter(so)._xmlid_for_export() for so in sale_orders if so.state not in ('cancel', 'draft')]
        nodes = []

        # Update sale order stages
        nodes.extend([
            etree.Comment("Update sale order stages"),
            E.function(
                model="sale.order",
                name="action_confirm",
                eval="[[%s]]" % ','.join("ref('%s')" % xmlid for xmlid in xmlids)
            )
        ])
        root = E.odoo(*nodes)
        xml = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        yield (filepath, xml)
        filenames.append(filepath)

    # SPECIFIC: Apply website theme if needed
    themes = [d for d in depends if d.startswith('theme_')]
    if themes:
        filepath = 'demo/website_theme_apply.xml'
        fns = [
            E.function(
                E.value(
                    model="ir.module.module",
                    eval=f"obj().env['ir.module.module'].search([('name', '=', '{theme}')]).ids"
                ),
                E.value(
                    model="ir.module.module",
                    eval="obj().env.ref('website.default_website')"
                ),
                model="ir.module.module",
                name="_theme_load",
                context="{'apply_new_theme': True}"
            ) for theme in themes
        ]
        # comment all but the first theme
        comments = [
            etree.Comment(
                etree.tostring(fn, pretty_print=True, encoding='UTF-8')
            ) for fn in fns[1:]
        ]
        nodes = [fns[0], *comments]
        root = E.odoo(*nodes)
        xml = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        yield (filepath, xml)
        try:
            # this demo file should be before 'demo/ir_ui_view.xml' if it exists.
            index = filenames.index('demo/ir_ui_view.xml')
            filenames.insert(index, filepath)
        except ValueError:
            filenames.append(filepath)

    # yield a warning file to notify circular dependencies and that some data haven't been exported
    warnings = []
    if circular_dependencies:
        circular_warnings = [
            f"({'demo' if is_demo else 'data'}) {' -> '.join(dep)}"
            for (is_demo, dep) in circular_dependencies
        ]
        warnings.extend([
            f"Found {len(circular_dependencies)} circular dependencies (you may have to change data loading order to avoid issues when importing):",
            *circular_warnings,
            "",
        ])

    if skipped_fields:
        warnings.extend([
            "The following relational data haven't been exported because they either refer",
            "to a model that Studio doesn't export, or have no XML id:",
            "",
        ])
        for xmlid, field, value in skipped_fields:
            warnings.extend([
                "Record: %s" % xmlid,
                "Model: %s" % field.model_name,
                "Field: %s" % field.name,
                "Type: %s" % field.type,
                "Value: %s (%s)" % (value, isinstance(value, models.BaseModel) and ', '.join("%r" % v.display_name for v in value) or "DB id: %s" % (value)),
                "",
            ])

    if warnings:
        yield ('warnings.txt', "\n".join(warnings))

    # yield files '__manifest__.py' and '__init__.py'
    demo_files = [f for f in filenames if f.startswith('demo/')]
    manifest = """# -*- coding: utf-8 -*-
{
    'name': %r,
    'version': %r,
    'category': 'Studio',
    'description': %s,
    'author': %r,
    'depends': [%s
    ],
    'data': [%s
    ],
    %s'license': %r,
}
""" % (
        module.display_name,
        module.installed_version,
        'u"""\n%s\n"""' % module.description,
        module.author,
        ''.join("\n        %r," % d for d in _clean_dependencies(depends)),
        ''.join("\n        %r," % f for f in filenames if f.startswith('data/')),
        "'demo': [%s\n    ],\n    " % ''.join("\n        %r," % f for f in demo_files) if demo_files else '',
        module.license,
    )
    manifest = manifest.encode('utf-8')
    yield ('__manifest__.py', manifest)
    yield ('__init__.py', b'')


# ============================== Serialization ==================================
def _serialize_model(module, model, records, fields_to_export, no_update, has_website, get_model_data):
    records_to_export, depends, binary_files = _prepare_records_to_export(module, model, records, fields_to_export, get_model_data)

    # create the XML containing the generated record nodes
    nodes = []

    # SPECIFIC: unlink the default main menu from the website if needed
    if model == 'website.menu' and any(r['url'] == '/default-main-menu' for r in records):
        # unlink the default menu from the website, in order to add our own
        nodes.append(
            E.function(
                E.value(
                    model="website.menu",
                    eval="obj().search([('website_id', '=', ref('website.default_website')), ('url', '=', '/default-main-menu')]).id"
                ),
                model="website.menu",
                name="unlink"
            )
        )

    if records_to_export:
        default_get_result = records_to_export[0].browse().default_get(fields_to_export)
    skipped_records = []
    for record in records_to_export:
        record_node, record_skipped = _serialize_record(module, model, record, fields_to_export, has_website, get_model_data, default_get_result)
        if record_node is not None:
            nodes.append(record_node)
        skipped_records.extend(record_skipped)

    # SPECIFIC: replace website pages arch if needed
    if model == 'ir.ui.view' and has_website:
        website_views = filter(lambda r: r['website_id'] and r['key'].startswith('website.') and r['create_uid'].id == 1, records_to_export)
        for view in website_views:
            exportid = get_model_data(view)._xmlid_for_export()
            nodes.append(
                E.function(
                    E.value(
                        model="ir.ui.view",
                        eval="obj().env['website'].with_context(website_id=obj().env.ref('website.default_website').id).viewref('%s').id" % view['key']
                    ),
                    E.value(
                        model="ir.ui.view",
                        eval="{'arch': obj().env.ref('%s').arch}" % exportid
                    ),
                    model="ir.ui.view",
                    name="write"
                )
            )

    if nodes:
        root = E.odoo(*nodes, noupdate="1") if no_update else E.odoo(*nodes)
        xml = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
    else:
        xml = None
    return xml, binary_files, depends, skipped_records


def _serialize_record(module, model, record, fields_to_export, has_website, get_model_data, default_get_data):
    """ Return an etree Element for the given record, together with a list of
        skipped field values (field value references a record without external id).
    """
    record_data = get_model_data(record)
    exportid = record_data._xmlid_for_export()
    skipped = []

    # Create the record node
    context = {}
    if record_data.studio:
        context.update({'studio': True})
    if record._name in ('product.template', 'product.template.attribute.line'):
        context.update({'create_product_product': False})
    if record._name == 'worksheet.template':
        context.update({'worksheet_no_generation': True})
    if exportid.startswith('website.configurator_'):
        exportid = exportid.replace('website.configurator_', 'configurator_')

    kwargs = {"id": exportid, "model": record._name}
    if context:
        kwargs["context"] = str(context)
    if module.name != _get_module_name(exportid):
        kwargs["forcecreate"] = "1"

    fields_nodes = []
    for name in fields_to_export:
        field = record._fields[name]
        field_element = None
        try:
            field_element = _serialize_field(record, field, has_website, get_model_data, default_get_data)
        except MissingXMLID:
            # the field value contains a record without an xml_id; skip it
            skipped.append((exportid, field, record[name]))

        if field_element is not None:
            fields_nodes.append(field_element)

    return E.record(*fields_nodes, **kwargs) if fields_nodes else None, skipped


def _serialize_field(record, field, has_website, get_model_data, default_get_data):
    """ Serialize the value of ``field`` on ``record`` as an etree Element. """
    default_value = default_get_data.get(field.name)
    value = record[field.name]
    if (not value and not default_value) or field.convert_to_cache(value, record) == field.convert_to_cache(default_value, record):
        return

    # SPECIFIC: make a unique key for ir.ui.view.key in case of website_id
    if has_website and field.name == 'key' and record._name == 'ir.ui.view' and record.website_id:
        value = f"studio_customization.{value}"

    if field.type in ('boolean', 'properties_definition', 'properties'):
        return E.field(name=field.name, eval=str(value))
    elif field.type == 'many2one_reference':
        reference_model = record[field.model_field]
        reference_value = reference_model and record.env[reference_model].browse(value) or False
        xmlid = get_model_data(reference_value)._xmlid_for_export()
        if reference_value:
            return E.field(name=field.name, ref=xmlid)
        else:
            return E.field(name=field.name, eval="False")
    elif field.type in ('many2many', 'one2many'):
        xmlids = [get_model_data(v)._xmlid_for_export() for v in value]
        return E.field(
            name=field.name,
            eval='[(6, 0, [%s])]' % ', '.join("ref('%s')" % xmlid for xmlid in xmlids),
        )

    if not value:
        return E.field(name=field.name, eval="False")
    elif (field.model_name, field.name) in XML_FIELDS:
        # Use an xml parser to remove new lines and indentations in value
        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
        return E.field(etree.XML(value, parser), name=field.name, type='xml')
    elif field.type == 'binary':
        return E.field(name=field.name, type="base64", file='studio_customization/' + _get_binary_field_file_name(field, record))
    elif field.type == 'datetime':
        return E.field(field.to_string(value), name=field.name)
    elif field.type in ('many2one', 'reference'):
        xmlid = get_model_data(value)._xmlid_for_export()
        return E.field(name=field.name, ref=xmlid)
    elif field.type in ('html', 'text'):
        # Wrap value in <![CDATA[]] to preserve it to be interpreted as XML markup, if any
        node = E.field(name=field.name)
        node.text = etree.CDATA(str(value))
        return node
    else:
        return E.field(str(value), name=field.name)


# ===================================== Utils ===================================
def _clean_dependencies(input_deps):
    """Return the minimal set of modules that ``depends`` depends on."""
    all_deps = request.env["ir.module.module.dependency"].all_dependencies(input_deps)
    deep_deps = dict()

    def get_deep_depends(module_name):
        """Return a set of all modules that ``module_name`` will install."""
        nonlocal deep_deps
        if module_name in deep_deps:
            return deep_deps[module_name]

        # initial case
        deep_deps[module_name] = set()

        # recursive case
        for dep in all_deps.get(module_name, []):
            deep_deps[module_name] |= {dep, *get_deep_depends(dep)}

        return deep_deps[module_name]

    for name in all_deps:
        get_deep_depends(name)

    # mods_deps = {item for sublist in zip(*all_deps.values()) for item in sublist}
    output_deps = set(input_deps)
    for mod, deps in deep_deps.items():
        if mod in input_deps:
            to_remove = deps - {mod}
            output_deps -= to_remove

    return sorted(output_deps)


def _get_binary_field_file_name(field, record):
    binary_filename = "%s-%s" % (record.id, field.name)
    if field.model_name == 'ir.attachment':
        binary_filename = "%s-%s" % (record.id, record.name.replace('/', '_').replace(' ', ''))

    return f"static/src/binary/{field.model_name.replace('.', '_')}/{binary_filename}"


def _get_module_name(xmlid):
    if xmlid.startswith('base.module_'):
        # len('base.module_') == 12
        return xmlid[12:]
    if not '.' in xmlid:
        return 'studio_customization'
    return xmlid.split('.', 1)[0]


def _get_relations(record, field):
    """ Return either a recordset that ``record`` depends on for ``field``, or a
        falsy value.
    """
    if not record[field.name]:
        return

    if field.type in ('many2one', 'one2many', 'many2many', 'reference'):
        return record[field.name]

    if field.type == 'many2one_reference':
        related_model = record[field.model_field]
        if not related_model:
            return
        return record.env[related_model].browse(record[field.name])

    if field.model_name == 'ir.model.fields':
        # Some fields (depends, related, relation_field) are of type char, but
        # refer to other fields that must be defined beforehand
        if field.name in ('depends', 'related'):
            # determine the fields that record depends on
            dep_fields = set()
            for dep_names in record[field.name].split(','):
                dep_model = record.env[record.model]
                for dep_name in dep_names.strip().split('.'):
                    dep_field = dep_model._fields[dep_name]
                    if not dep_field.automatic:
                        dep_fields.add(dep_field)
                    if dep_field.relational:
                        dep_model = record.env[dep_field.comodel_name]
            # determine the 'ir.model.fields' corresponding to 'dep_fields'
            if dep_fields:
                return record.search(OR([
                    ['&', ('model', '=', dep_field.model_name), ('name', '=', dep_field.name)]
                    for dep_field in dep_fields
                ]))
        elif field.name == 'relation_field':
            # The field 'relation_field' on 'ir.model.fields' is of type char,
            # but it refers to another field that must be defined beforehand
            return record.search([('model', '=', record.relation), ('name', '=', record.relation_field)])

    # Fields 'res_model' and 'binding_model' on 'ir.actions.act_window' and 'model'
    # on 'ir.actions.report' are of type char but refer to models that may
    # be defined in other modules and those modules need to be listed as
    # dependencies of the exported module
    if field.model_name == 'ir.actions.act_window' and field.name in ('res_model', 'binding_model'):
        return record.env['ir.model']._get(record[field.name])
    if field.model_name == 'ir.actions.report' and field.name == 'model':
        return record.env['ir.model']._get(record.model)


def _prepare_records_to_export(module, model, records, fields_to_export, get_model_data):
    """Returns
        - A sorted list of records that satisfies inter-record dependencies
        - Additional module dependencies
        - Additional binary files
    """

    depends = set()

    def add_dependency(module_name):
        if module_name and module_name != module.name and module_name != '__export__':
            depends.add(module_name)

    binary_files = []

    fields = [records._fields[name] for name in fields_to_export]
    record_deps = OrderedDict.fromkeys(records, records.browse())
    for record in records:
        record_data = get_model_data(record)
        exportid = record_data._xmlid_for_export()
        module_name = _get_module_name(exportid)

        # data depends on a record from another module
        add_dependency(record._original_module)  # module that first created the record's model
        add_dependency(record._module)  # module that last extended the record's model
        add_dependency(module_name)  # module from which the record was defined

        for field in fields:
            for m in field._modules:
                add_dependency(m)
            # create files for binary fields
            if field.type == 'binary' and record[field.name]:
                value = record[field.name]
                try:
                    binary_data = b64decode(value)
                except (binascii.Error, TypeError):
                    binary_data = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                binary_files.append((_get_binary_field_file_name(field, record), binary_data))

            # handle relational fields
            rel_records = _get_relations(record, field)
            if not rel_records:
                continue

            for rel_record in rel_records:
                try:
                    rel_xmlid = get_model_data(rel_record)._xmlid_for_export()
                except MissingXMLID:
                    # skip records that don't have an xmlid,
                    # as they won't be exported and will
                    # end up in the warning.txt file anyway
                    continue
                add_dependency(_get_module_name(rel_xmlid))

            if rel_records._name == model:
                # fill in inter-record dependencies
                record_deps[record] |= rel_records

        if record._name == 'ir.model.fields' and record.ttype == 'monetary':
            # add a dependency on the currency field
            rel_record = record._get(record.model, 'currency_id') or record._get(record.model, 'x_currency_id')
            if rel_record:
                rel_xmlid = get_model_data(rel_record)._xmlid_for_export()
                add_dependency(_get_module_name(rel_xmlid))
                record_deps[record] |= rel_record

    # sort records to satisfy inter-record dependencies
    records = topological_sort(record_deps)

    return records, depends, binary_files


def _has_website():
    return request.env['ir.module.module'].search_count([('state', '=', 'installed'), ('name', '=', 'website')]) == 1


def ir_model_data_getter(data):
    """ Returns a function that returns the data (either ir.model.data or studio.export.wizard.data record) of a given record """
    # {(model_name, record_id): ir_model_data_record(s)}
    cache = data.grouped(lambda d: (d.model, d.res_id))

    def get(record):
        """ Return the ir_model_data linked to the ``record``.
            Raise a ``MissingXMLID`` if ir_model_data does not exist.
        """
        key = (record._name, record.id)
        if key not in cache or not cache[key]:
            # prefetch when possible
            for data in record.env['ir.model.data'].sudo().search(
                [('model', '=', record._name), ('res_id', 'in', list(record._prefetch_ids))], order='id',
            ):
                key_data = (data.model, data.res_id)
                if key_data not in cache:  # Only one record in the cache
                    cache[key_data] = data

        if key not in cache:
            raise MissingXMLID(record)
        return cache[key]

    return get


class MissingXMLID(Exception):
    def __init__(self, record):
        super(MissingXMLID, self).__init__("Missing XMLID: %s (%s)" % (record, record.display_name))
