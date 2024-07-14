# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import OrderedDict
from contextlib import closing
import io
from lxml import etree
from lxml.builder import E
import os.path
import zipfile

from odoo import models
from odoo.osv.expression import OR
from odoo.tools import topological_sort

# list of models to export (the order ensures that dependencies are satisfied)
MODELS_TO_EXPORT = [
    'res.groups',
    'report.paperformat',
    'ir.model',
    'ir.model.fields',
    'ir.ui.view',
    'ir.actions.act_window',
    'ir.actions.act_window.view',
    'ir.actions.report',
    'mail.template',
    'ir.actions.server',
    'ir.ui.menu',
    'ir.filters',
    'base.automation',
    'ir.model.access',
    'ir.rule',
    'ir.default',
    'studio.approval.rule',
]
# list of fields to export by model
FIELDS_TO_EXPORT = {
    'base.automation': [
        'action_server_ids', 'active', 'filter_domain', 'filter_pre_domain',
        'last_run', 'on_change_field_ids', 'trg_date_id', 'trg_date_range',
        'trg_date_range_type', 'trigger'
    ],
    'ir.actions.act_window': [
        'binding_model_id', 'binding_type', 'binding_view_types',
        'context', 'domain', 'filter',
        'groups_id', 'help', 'limit', 'name', 'res_model', 'search_view_id',
        'target', 'type', 'usage', 'view_id', 'view_mode'
    ],
    'ir.actions.act_window.view': ['act_window_id', 'multi', 'sequence', 'view_id', 'view_mode'],
    'ir.actions.report': [
        'attachment', 'attachment_use', 'binding_model_id', 'binding_type', 'binding_view_types', 'groups_id', 'model',
        'multi', 'name', 'paperformat_id', 'report_name', 'report_type'
    ],
    'ir.actions.server': [
        'binding_model_id', 'binding_type', 'binding_view_types', 'child_ids', 'code', 'crud_model_id', 'help',
        'link_field_id', 'model_id', 'name', 'sequence', 'state'
    ],
    'ir.filters': [
        'action_id', 'active', 'context', 'domain', 'is_default', 'model_id', 'name', 'sort'
    ],
    'ir.model': ['info', 'is_mail_thread', 'is_mail_activity', 'model', 'name', 'state', 'transient'],
    'ir.model.access': [
        'active', 'group_id', 'model_id', 'name', 'perm_create', 'perm_read', 'perm_unlink',
        'perm_write'
    ],
    'ir.model.fields': [
        'complete_name', 'compute', 'copied', 'depends', 'domain', 'field_description', 'groups',
        'help', 'index', 'model', 'model_id', 'name', 'on_delete', 'readonly', 'related',
        'relation', 'relation_field', 'relation_table', 'required', 'selectable', 'selection',
        'size', 'state', 'store', 'tracking', 'translate',
        'ttype', "currency_field",
    ],
    'ir.rule': [
        'active', 'domain_force', 'groups', 'model_id', 'name', 'perm_create', 'perm_read',
        'perm_unlink', 'perm_write'
    ],
    'ir.ui.menu': ['action', 'active', 'groups_id', 'name', 'parent_id', 'sequence', 'web_icon'],
    'ir.ui.view': [
        'active', 'arch', 'groups_id', 'inherit_id', 'key', 'mode', 'model', 'name',
        'priority', 'type'
    ],
    'mail.template': [
        'auto_delete', 'body_html', 'email_cc', 'email_from', 'email_to', 'lang',
        'model_id', 'name', 'partner_to', 'ref_ir_act_window',
        'reply_to', 'report_template_ids', 'scheduled_date',
        'subject', 'use_default_to'
    ],
    'res.groups': ['color', 'comment', 'implied_ids', 'name', 'share'],
    'ir.default': ['field_id', 'condition', 'json_value'],
    'studio.approval.rule': ['group_id', 'model_id', 'method', 'action_id', 'name', 'message',
        'exclusive_user', 'domain', 'can_validate'],
}
# list of relational fields to NOT export, by model
FIELDS_NOT_TO_EXPORT = {
    'base.automation': ['trg_date_calendar_id'],
    'ir.actions.server': ['partner_ids'],
    'ir.filters': ['user_id'],
    'mail.template': ['attachment_ids', 'mail_server_id'],
    'report.paperformat': ['report_ids'],
    'res.groups': ['category_id', 'users'],
}
# The fields whose value must be wrapped in <![CDATA[]]>
CDATA_FIELDS = [
    ('ir.actions.server', 'code'), ('ir.model.fields', 'compute'), ('ir.rule', 'domain_force'),
    ('ir.actions.act_window', 'help'), ('ir.actions.server', 'help'), ('ir.model.fields', 'help')
]
# The fields whose value is some XML content
XML_FIELDS = [('ir.ui.view', 'arch')]


def generate_archive(module, data):
    """ Returns a zip file containing the given module with the given data. """
    with closing(io.BytesIO()) as f:
        with zipfile.ZipFile(f, 'w') as archive:
            for filename, content in generate_module(module, data):
                archive.writestr(os.path.join(module.name, filename), content)
        return f.getvalue()


def generate_module(module, data):
    """ Return an iterator of pairs (filename, content) to put in the exported
        module. Returned filenames are local to the module directory.
        Only exports models in MODELS_TO_EXPORT.
        Groups exported data by model in separated files.
        The content of the files is yielded as an encoded bytestring (utf-8)
    """
    get_xmlid = xmlid_getter()

    # Generate xml files and yield them
    filenames = []          # filenames to include in the module to export
    # depends contains module dependencies of the module to export, as a result
    # we add web_studio by default to deter importing studio customizations
    # in community databases
    depends = set([u'web_studio'])
    skipped = []            # non-exported field values

    for model in MODELS_TO_EXPORT:
        # determine records to export for model
        model_data = data.filtered(lambda r: r.model == model)
        records = data.env[model].browse(model_data.mapped('res_id')).exists()
        if not records:
            continue

        # retrieve module and inter-record dependencies
        fields = [records._fields[name] for name in get_fields_to_export(records)]
        record_deps = OrderedDict.fromkeys(records, records.browse())
        for record in records:
            xmlid = get_xmlid(record)
            module_name = xmlid.split('.', 1)[0]
            if module_name != module.name:
                # data depends on a record from another module
                depends.add(module_name)
            for field in fields:
                rel_records = get_relations(record, field)
                if not rel_records:
                    continue
                for rel_record in rel_records:
                    rel_xmlid = get_xmlid(rel_record, check=False)
                    if rel_xmlid and rel_xmlid.split('.')[0] != module.name:
                        # data depends on a record from another module
                        depends.add(rel_xmlid.split('.')[0])
                if rel_records._name == model:
                    # fill in inter-record dependencies
                    record_deps[record] |= rel_records
            if record._name == 'ir.model.fields' and record.ttype == 'monetary':
                # add a dependency on the currency field
                if record.currency_field:
                    rel_record = record._get(record.model, record.currency_field)
                else:
                    rel_record = record._get(record.model, 'currency_id') or record._get(record.model, 'x_currency_id')
                rel_xmlid = get_xmlid(rel_record, check=False)
                if rel_xmlid and rel_xmlid.split('.')[0] != module.name:
                    # data depends on a record from another module
                    depends.add(rel_xmlid.split('.')[0])
                record_deps[record] |= rel_record

        # sort records to satisfy inter-record dependencies
        records = topological_sort(record_deps)

        # create the XML containing the generated record nodes
        nodes = []
        for record in records:
            xmlid = get_xmlid(record)
            if xmlid.split('.', 1)[0] != '__export__':
                record_node, record_skipped = generate_record(record, get_xmlid)
                nodes.append(record_node)
                skipped.extend(record_skipped)
        root = E.odoo(*nodes)
        xml = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)

        # add the XML file to the archive
        filename = '/'.join(['data', '%s.xml' % model.replace('.', '_')])
        yield (filename, xml)
        filenames.append(filename)

    # yield a warning file to notify that some data haven't been exported
    if skipped:
        content = [
            "The following relational data haven't been exported because they either refer",
            "to a model that Studio doesn't export, or have no XML id:",
            "",
        ]
        for xmlid, field, value in skipped:
            content.append("Record: %s" % xmlid)
            content.append("Model: %s" % field.model_name)
            content.append("Field: %s" % field.name)
            content.append("Type: %s" % field.type)
            content.append("Value: %s (%s)" % (value, ', '.join("%r" % v.display_name for v in value)))
            content.append("")
        yield ('warning.txt', "\n".join(content))

    # yield files '__manifest__.py' and '__init__.py'
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
    'application': %s,
    'license': %r,
}
""" % (
        module.display_name,
        module.installed_version,
        'u"""\n%s\n"""' % module.description,
        module.author,
        ''.join("\n        %r," % d for d in sorted(depends - {'__export__'})),
        ''.join("\n        %r," % f for f in filenames),
        module.application,
        module.license,
    )
    manifest = manifest.encode('utf-8')

    yield ('__manifest__.py', manifest)
    yield ('__init__.py', b'')


def get_relations(record, field):
    """ Return either a recordset that ``record`` depends on for ``field``, or a
        falsy value.
    """
    if not record[field.name]:
        return

    if field.type in ('many2one', 'one2many', 'many2many', 'reference'):
        return record[field.name]

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


def generate_record(record, get_xmlid):
    """ Return an etree Element for the given record, together with a list of
        skipped field values (fields in FIELDS_NOT_TO_EXPORT).
    """
    xmlid = get_xmlid(record)
    skipped = []

    # Create the record node
    record_node = E.record(id=xmlid, model=record._name, context="{'studio': True}")
    for name in get_fields_to_export(record):
        field = record._fields[name]
        try:
            record_node.append(generate_field(record, field, get_xmlid))
        except MissingXMLID:
            # the field value contains a record without an xml_id; skip it
            skipped.append((xmlid, field, record[name]))

    # The record contains relational data that don't export, so register it in skipped
    for name in FIELDS_NOT_TO_EXPORT.get(record._name, ()):
        if record[name]:
            field = record._fields[name]
            skipped.append((xmlid, field, record[name]))

    return record_node, skipped

def get_fields_to_export(record):
    fields_to_export = FIELDS_TO_EXPORT.get(record._name)
    if not fields_to_export:
        # deduce the fields_to_export from available data
        fields_to_export = set(record._fields.keys())
        fields_to_export -= set(models.MAGIC_COLUMNS)
        if FIELDS_NOT_TO_EXPORT.get(record._name):
            fields_to_export -= set(FIELDS_NOT_TO_EXPORT.get(record._name))
    return fields_to_export

def generate_field(record, field, get_xmlid):
    """ Serialize the value of ``field`` on ``record`` as an etree Element. """
    value = record[field.name]
    if field.type == 'boolean':
        return E.field(name=field.name, eval=str(value))
    elif field.type in ('many2one', 'reference'):
        if value:
            return E.field(name=field.name, ref=get_xmlid(value))
        else:
            return E.field(name=field.name, eval=u"False")
    elif field.type in ('many2many', 'one2many'):
        return E.field(
            name=field.name,
            eval='[(6, 0, [%s])]' % ', '.join("ref('%s')" % get_xmlid(v) for v in value),
        )
    else:
        if not value:
            return E.field(name=field.name, eval=u"False")
        elif (field.model_name, field.name) in CDATA_FIELDS:
            # Wrap value in <![CDATA[]] to preserve it to be interpreted as XML markup
            node = E.field(name=field.name)
            node.text = etree.CDATA(str(value))
            return node
        elif (field.model_name, field.name) in XML_FIELDS:
            # Use an xml parser to remove new lines and indentations in value
            parser = etree.XMLParser(remove_blank_text=True)
            return E.field(etree.XML(value, parser), name=field.name, type='xml')
        else:
            return E.field(str(value), name=field.name)


def xmlid_getter():
    """ Return a function that returns the xml_id of a given record. """
    cache = {}

    def get(record, check=True):
        """ Return the xml_id of ``record``.
            Raise a ``MissingXMLID`` if ``check`` is true and xml_id is empty.
        """
        try:
            res = cache[record]
        except KeyError:
            # prefetch when possible
            records = record.browse(record._prefetch_ids)
            for rid, val in records.get_external_id().items():
                cache[record.browse(rid)] = val
            res = cache[record]
        if check and not res:
            raise MissingXMLID(record)
        return res

    return get


class MissingXMLID(Exception):
    def __init__(self, record):
        super(MissingXMLID, self).__init__("Missing XMLID: %s (%s)" % (record, record.display_name))
